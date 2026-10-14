"""
Wipes ALL existing data (demo users, papers, logs, alerts) and creates a
single Administrator account for you.

As Administrator you can do everything yourself: upload papers (they get
genuinely AES-256 encrypted, SHA-256 hashed, and RSA-signed), approve or
reject them, view the AI alerts and audit log, and manage other users
later if you want to add real Paper Setters/Moderators/etc.

Run with:  python -m app.services.reset_and_create_admin
You'll be asked for your name, email, and a password.
"""
import asyncio
import uuid
from datetime import datetime
from getpass import getpass

from app.database import database
from app.security.auth_utils import hash_password


async def main():
    database.connect()

    print("This will DELETE all existing users, papers, audit logs, and alerts.")
    confirm = input("Type YES to continue: ").strip()
    if confirm != "YES":
        print("Cancelled -- nothing was deleted.")
        database.close()
        return

    for coll in [database.users, database.papers, database.audit_logs, database.alerts, database.reports]:
        await coll.delete_many({})
    print("All demo data cleared.\n")

    name = input("Your name: ").strip()
    email = input("Your email (used to log in): ").strip()
    password = getpass("Choose a password: ").strip()

    admin_doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "role": "administrator",
        "institution": None,
        "hashed_password": hash_password(password),
        "created_at": datetime.utcnow(),
        "last_login": None,
        "is_active": True,
        "failed_login_count": 0,
        "known_devices": [],
        "known_ips": [],
    }
    await database.users.insert_one(admin_doc)

    print(f"\nDone! Your database is now empty except for your account.")
    print(f"Log in at http://localhost:3000/login with:")
    print(f"  Email:    {email}")
    print(f"  Password: (the one you just typed)")
    print(f"\nAs Administrator you can upload, approve, and reject papers yourself,")
    print(f"and invite other users later from the User Management page.")

    database.close()


if __name__ == "__main__":
    asyncio.run(main())
