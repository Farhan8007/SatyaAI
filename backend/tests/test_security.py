"""
Tests for Security Lead implementation:
- Day 2: RSA key persistence across fresh processes without regeneration
- Day 2: Concurrent audit log writes and hash-chain integrity verification
- Day 5: Release-window enforcement on paper unlock (rejecting premature unlocks)
"""
import asyncio
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
from fastapi import HTTPException

from app.models.paper import ApprovalStatus
from app.routers.papers import unlock_paper
from app.security.encryption import get_rsa_key_paths
from app.services.audit_service import record_audit_log, verify_chain, verify_chain_integrity
import app.routers.papers as papers_module
import app.services.audit_service as audit_module


def test_rsa_key_reload_across_fresh_process():
    """Verify RSA keys persist to PEM on disk and can be loaded in a fresh process

    without regeneration, verifying signatures across process boundaries.
    """
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    with tempfile.TemporaryDirectory() as temp_dir:
        sig_file = os.path.join(temp_dir, "test.sig")
        priv_path = os.path.join(temp_dir, "satya_rsa_private.pem")
        pub_path = os.path.join(temp_dir, "satya_rsa_public.pem")

        # Process 1: Generate & save keys, sign payload
        p1_code = f"""
import os
os.environ['RSA_KEYS_DIR'] = {repr(temp_dir)}
from app.security.encryption import sign_data, get_rsa_key_paths
priv, pub = get_rsa_key_paths()
assert priv == {repr(priv_path)}
assert pub == {repr(pub_path)}
sig = sign_data(b'cross-process examination payload 42')
with open({repr(sig_file)}, 'w') as f:
    f.write(sig)
print('P1_SUCCESS')
"""
        res1 = subprocess.check_output(
            [sys.executable, "-c", p1_code],
            cwd=backend_dir,
            text=True,
        )
        assert "P1_SUCCESS" in res1
        assert os.path.isfile(priv_path)
        assert os.path.isfile(pub_path)

        p1_mtime_priv = os.path.getmtime(priv_path)
        p1_mtime_pub = os.path.getmtime(pub_path)

        # Process 2: Launch a completely fresh process with the same RSA_KEYS_DIR.
        # It must load the existing keys from disk without regenerating them.
        p2_code = f"""
import os
os.environ['RSA_KEYS_DIR'] = {repr(temp_dir)}
from app.security.encryption import verify_signature
with open({repr(sig_file)}) as f:
    sig = f.read().strip()
assert verify_signature(b'cross-process examination payload 42', sig), 'Signature verification failed in process 2'
assert not verify_signature(b'tampered payload', sig), 'Tampered verification should have returned False'
print('P2_SUCCESS')
"""
        res2 = subprocess.check_output(
            [sys.executable, "-c", p2_code],
            cwd=backend_dir,
            text=True,
        )
        assert "P2_SUCCESS" in res2

        # Verify keys were not re-created or modified by process 2
        assert os.path.getmtime(priv_path) == p1_mtime_priv, "Private key file should not be regenerated"
        assert os.path.getmtime(pub_path) == p1_mtime_pub, "Public key file should not be regenerated"


def test_concurrent_audit_chain_integrity():
    """Verify that concurrent audit log writes protected by the asyncio lock

    produce a strictly valid, uncorrupted linear hash chain.
    """
    async def _run():
        stored_logs = []

        async def mock_find_one(sort=None):
            # Simulate slight async delay to expose race conditions if lock was absent
            await asyncio.sleep(0.002)
            if stored_logs:
                return stored_logs[-1]
            return None

        async def mock_insert_one(doc):
            await asyncio.sleep(0.002)
            stored_logs.append(doc)

        mock_audit_coll = AsyncMock()
        mock_audit_coll.find_one.side_effect = mock_find_one
        mock_audit_coll.insert_one.side_effect = mock_insert_one

        with patch.object(type(audit_module.database), "audit_logs", new_callable=PropertyMock, return_value=mock_audit_coll):
            # Launch 20 concurrent writes
            async def write_log(i):
                return await record_audit_log(
                    user_id=f"user-{i}",
                    user_name=f"User {i}",
                    role="examination_centre",
                    ip_address=f"10.0.0.{i}",
                    device="agent",
                    action="CONCURRENT_ACTION",
                    status="SUCCESS",
                )

            tasks = [write_log(i) for i in range(20)]
            await asyncio.gather(*tasks)

            assert len(stored_logs) == 20

            # Verify chain integrity using both verify_chain and verify_chain_integrity
            assert verify_chain_integrity(stored_logs), "Chain integrity should be valid with serialized lock"
            assert verify_chain(stored_logs), "verify_chain should also confirm valid chain"

            # Verify tampering is detected if any single log is modified
            tampered_logs = [dict(log) for log in stored_logs]
            tampered_logs[5]["action"] = "TAMPERED_ACTION"
            assert not verify_chain_integrity(tampered_logs), "Tampered entry must be detected"
            assert not verify_chain(tampered_logs), "verify_chain must also detect tampered entry"

    asyncio.run(_run())


def test_premature_unlock_rejected():
    """Day 5: Verify that unlocking before the release window is rejected with 403

    and emits a PREMATURE_UNLOCK_ATTEMPT audit event.
    """
    async def _run():
        # Exam is 2 hours in the future, unlock window is 30 mins
        future_exam_date = datetime.now(timezone.utc) + timedelta(hours=2)

        fake_paper = {
            "id": "paper-early",
            "title": "Quantum Physics",
            "subject": "Physics",
            "exam_date": future_exam_date,
            "exam_centre": "Centre-01",
            "setter_id": "setter-1",
            "status": ApprovalStatus.approved,
            "sha256_hash": "hash123",
            "unlock_window_minutes": 30,
            "unlock_time": None,
        }

        exam_centre_user = {
            "sub": "centre-user-1",
            "role": "examination_centre",
            "name": "Centre Supervisor",
            "institution": "Centre-01",
        }

        mock_papers_coll = AsyncMock()
        mock_papers_coll.find_one.return_value = fake_paper

        with patch.object(type(papers_module.database), "papers", new_callable=PropertyMock, return_value=mock_papers_coll), \
             patch("app.routers.papers.record_audit_log", new_callable=AsyncMock) as mock_audit:

            with pytest.raises(HTTPException) as exc_info:
                await unlock_paper(paper_id="paper-early", user=exam_centre_user)

            assert exc_info.value.status_code == 403
            assert "Exam release window not open yet" in exc_info.value.detail

            # Verify PREMATURE_UNLOCK_ATTEMPT audit event was emitted
            mock_audit.assert_called_once()
            audit_kwargs = mock_audit.call_args.kwargs
            assert audit_kwargs["action"] == "PREMATURE_UNLOCK_ATTEMPT"
            assert audit_kwargs["status"] == "FAILED"
            assert audit_kwargs["paper_id"] == "paper-early"

    asyncio.run(_run())


def test_valid_window_unlock_succeeds():
    """Day 5: Verify that unlocking within the release window succeeds and sets unlock_time."""
    async def _run():
        # Exam is 15 mins in the future, unlock window is 30 mins -> within window!
        valid_exam_date = datetime.now(timezone.utc) + timedelta(minutes=15)

        fake_paper = {
            "id": "paper-window-ok",
            "title": "Organic Chemistry",
            "subject": "Chemistry",
            "exam_date": valid_exam_date,
            "exam_centre": "Centre-01",
            "setter_id": "setter-1",
            "status": ApprovalStatus.approved,
            "sha256_hash": "hash456",
            "unlock_window_minutes": 30,
            "unlock_time": None,
        }

        exam_centre_user = {
            "sub": "centre-user-1",
            "role": "examination_centre",
            "name": "Centre Supervisor",
            "institution": "Centre-01",
        }

        mock_papers_coll = AsyncMock()
        mock_papers_coll.find_one.return_value = fake_paper
        mock_papers_coll.update_one.return_value = AsyncMock()

        with patch.object(type(papers_module.database), "papers", new_callable=PropertyMock, return_value=mock_papers_coll), \
             patch("app.routers.papers.record_audit_log", new_callable=AsyncMock) as mock_audit:

            res = await unlock_paper(paper_id="paper-window-ok", user=exam_centre_user)

            assert res["detail"] == "Paper unlocked for secure download."
            assert res["sha256_hash"] == "hash456"

            # Check update_one was called to persist unlock_time
            mock_papers_coll.update_one.assert_called_once()
            update_call = mock_papers_coll.update_one.call_args
            assert "unlock_time" in update_call[0][1]["$set"]

            # Check UNLOCK_PAPER was logged
            mock_audit.assert_called_once()
            audit_kwargs = mock_audit.call_args.kwargs
            assert audit_kwargs["action"] == "UNLOCK_PAPER"
            assert audit_kwargs["status"] == "SUCCESS"

    asyncio.run(_run())
