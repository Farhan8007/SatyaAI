"""
Generates realistic sample data so the platform is demoable without
a real institution's data: users across all 5 roles, question papers
in various approval states, 500+ chained audit logs (including
injected suspicious patterns), and the resulting AI alerts.

Run with:  python -m app.services.seed_data
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta

from faker import Faker

from app.database import database
from app.config import settings
from app.security.auth_utils import hash_password
from app.security.encryption import sha256_hash, sign_data, aes_encrypt, chain_hash
from app.ai.anomaly_detector import AnomalyDetector, risk_level_from_score
from app.ai.explainer import explain
from app.services.audit_service import set_detector

fake = Faker()
random.seed(7)
Faker.seed(7)

ROLES = ["administrator", "paper_setter", "moderator", "examination_centre", "security_auditor"]
ACTIONS = ["LOGIN", "UPLOAD_PAPER", "APPROVE_PAPER", "REJECT_PAPER", "DOWNLOAD_PAPER", "UNLOCK_PAPER"]
DEVICES = ["Windows-Chrome", "MacOS-Safari", "Windows-Edge", "Linux-Firefox", "Android-Chrome"]
LOCATIONS = ["Mumbai, IN", "Pune, IN", "Kolhapur, IN", "Delhi, IN", "Bengaluru, IN", "Unknown VPN Exit"]


async def clear_all():
    for coll in [database.users, database.papers, database.audit_logs, database.alerts]:
        await coll.delete_many({})


async def seed_users(n_extra: int = 15) -> list[dict]:
    users = []
    # one guaranteed login per role for demo purposes
    for role in ROLES:
        users.append({
            "id": str(uuid.uuid4()),
            "name": fake.name(),
            "email": f"{role}@satyaai.demo",
            "role": role,
            "institution": "Demo Institute of Technology",
            "hashed_password": hash_password("Password@123"),
            "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 300)),
            "last_login": None,
            "is_active": True,
            "failed_login_count": 0,
            "known_devices": [random.choice(DEVICES)],
            "known_ips": [fake.ipv4()],
        })
    for _ in range(n_extra):
        role = random.choice(ROLES)
        users.append({
            "id": str(uuid.uuid4()),
            "name": fake.name(),
            "email": fake.unique.email(),
            "role": role,
            "institution": fake.company(),
            "hashed_password": hash_password("Password@123"),
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 300)),
            "last_login": None,
            "is_active": True,
            "failed_login_count": 0,
            "known_devices": [random.choice(DEVICES)],
            "known_ips": [fake.ipv4()],
        })
    await database.users.insert_many(users)
    return users


async def seed_papers(users: list[dict], n: int = 40) -> list[dict]:
    setters = [u for u in users if u["role"] == "paper_setter"] or users
    papers = []
    for _ in range(n):
        setter = random.choice(setters)
        content = fake.paragraph(nb_sentences=20).encode()
        status = random.choices(
            ["approved", "pending", "rejected"], weights=[0.6, 0.25, 0.15]
        )[0]
        papers.append({
            "id": str(uuid.uuid4()),
            "title": f"{fake.job()} - {random.choice(['Mid Sem', 'End Sem', 'Unit Test'])}",
            "subject": fake.catch_phrase(),
            "exam_date": datetime.utcnow() + timedelta(days=random.randint(1, 60)),
            "exam_centre": fake.city(),
            "setter_id": setter["id"],
            "setter_name": setter["name"],
            "status": status,
            "sha256_hash": sha256_hash(content),
            "signature": sign_data(content),
            "is_encrypted": True,
            "unlock_time": None,
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 90)),
            "remarks": fake.sentence() if status == "rejected" else None,
            "encrypted_blob": aes_encrypt(content),
        })
    await database.papers.insert_many(papers)
    return papers


def _make_log(prev_hash: str, user: dict, action: str, status: str, timestamp: datetime,
              paper_id: str | None, suspicious: bool = False) -> dict:
    entry_id = str(uuid.uuid4())
    is_new_device = suspicious and random.random() < 0.7
    is_new_ip = suspicious and random.random() < 0.7
    downloads_last_hour = random.randint(3, 6) if suspicious and action == "DOWNLOAD_PAPER" else random.randint(0, 1)
    locations_last_24h = random.randint(2, 4) if suspicious else 1
    is_bulk_download = suspicious and action == "DOWNLOAD_PAPER" and random.random() < 0.4
    skipped_approval = suspicious and action == "UNLOCK_PAPER" and random.random() < 0.3
    permission_escalation = suspicious and random.random() < 0.15

    hour = random.choice([1, 2, 3, 23]) if suspicious and random.random() < 0.5 else timestamp.hour

    entry_data = f"{entry_id}|{user['id']}|{action}|{status}|{timestamp.isoformat()}"
    entry_hash = chain_hash(prev_hash, entry_data)

    return {
        "id": entry_id,
        "timestamp": timestamp,
        "user_id": user["id"],
        "user_name": user["name"],
        "role": user["role"],
        "ip_address": fake.ipv4(),
        "location": random.choice(LOCATIONS),
        "device": random.choice(DEVICES),
        "browser": random.choice(["Chrome 124", "Safari 17", "Edge 124", "Firefox 126"]),
        "action": action,
        "paper_id": paper_id,
        "status": status,
        "hash": entry_hash,
        "prev_hash": prev_hash,
        "hour_of_day": hour,
        "is_new_device": is_new_device,
        "is_new_ip": is_new_ip,
        "is_failed_login": status == "FAILED",
        "downloads_last_hour": downloads_last_hour,
        "locations_last_24h": locations_last_24h,
        "is_bulk_download": is_bulk_download,
        "skipped_approval": skipped_approval,
        "permission_escalation": permission_escalation,
    }


async def seed_audit_logs(users: list[dict], papers: list[dict], n: int = 520) -> list[dict]:
    logs = []
    prev_hash = "GENESIS"
    now = datetime.utcnow()

    # ~8% of logs are deliberately suspicious so the AI has real signal to find
    suspicious_indices = set(random.sample(range(n), k=int(n * 0.08)))

    for i in range(n):
        user = random.choice(users)
        action = random.choice(ACTIONS)
        status = "FAILED" if action == "LOGIN" and random.random() < 0.1 else "SUCCESS"
        paper = random.choice(papers) if action in ("DOWNLOAD_PAPER", "APPROVE_PAPER", "REJECT_PAPER", "UNLOCK_PAPER") else None
        timestamp = now - timedelta(minutes=random.randint(0, 60 * 24 * 45))
        timestamp = timestamp.replace(microsecond=(timestamp.microsecond // 1000) * 1000)

        log = _make_log(
            prev_hash, user, action, status, timestamp,
            paper["id"] if paper else None,
            suspicious=i in suspicious_indices,
        )
        prev_hash = log["hash"]
        logs.append(log)

    logs.sort(key=lambda l: l["timestamp"])
    # Re-chain in true chronological order so verify_chain_integrity works later
    prev_hash = "GENESIS"
    for log in logs:
        entry_data = f"{log['id']}|{log['user_id']}|{log['action']}|{log['status']}|{log['timestamp'].isoformat()}"
        log["hash"] = chain_hash(prev_hash, entry_data)
        log["prev_hash"] = prev_hash
        prev_hash = log["hash"]

    await database.audit_logs.insert_many(logs)
    return logs


async def train_and_generate_alerts(logs: list[dict]) -> AnomalyDetector:
    import pandas as pd
    from app.ai.anomaly_detector import FEATURE_COLUMNS

    df = pd.DataFrame(logs)
    detector = AnomalyDetector(contamination=0.08)
    detector.fit(df)
    set_detector(detector)

    alerts = []
    for log in logs:
        features = {col: log.get(col, 0) for col in FEATURE_COLUMNS}
        result = detector.score(features)
        if result.is_anomaly or result.risk_score >= 35:
            explanation = explain(features, result.risk_score)
            alerts.append({
                "id": str(uuid.uuid4()),
                "created_at": log["timestamp"],
                "user_id": log["user_id"],
                "user_name": log["user_name"],
                "risk_score": result.risk_score,
                "risk_level": risk_level_from_score(result.risk_score),
                "reasons": explanation.reasons,
                "confidence": explanation.confidence,
                "recommended_action": explanation.recommended_action,
                "related_paper_id": log.get("paper_id"),
                "related_log_ids": [log["id"]],
                "resolved": random.random() < 0.3,
            })
    if alerts:
        await database.alerts.insert_many(alerts)
    return detector


async def main():
    database.connect()
    print("Clearing existing collections...")
    await clear_all()

    print("Seeding users...")
    users = await seed_users()

    print("Seeding question papers...")
    papers = await seed_papers(users)

    print("Seeding audit logs (this generates 500+ chained entries)...")
    logs = await seed_audit_logs(users, papers)

    print("Training Isolation Forest and generating explainable alerts...")
    await train_and_generate_alerts(logs)

    print(f"Done. Users={len(users)} Papers={len(papers)} Logs={len(logs)}")
    print("Demo logins (password: Password@123):")
    for role in ROLES:
        print(f"  {role}@satyaai.demo")
    database.close()


if __name__ == "__main__":
    asyncio.run(main())
