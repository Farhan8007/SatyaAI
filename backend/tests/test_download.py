"""
Unit & Integration tests for Day 3 Secure Paper Download flow:
- Real AES-256 decryption
- SHA-256 hash integrity check
- RSA-PSS digital signature verification
- Tamper detection handling & audit logging
- Centre & Role access scoping
"""
import asyncio
import io
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, PropertyMock, patch

from fastapi import HTTPException
from app.models.paper import ApprovalStatus
from app.routers.papers import download_paper
from app.security.encryption import (
    aes_encrypt,
    aes_decrypt,
    sha256_hash,
    sign_data,
    verify_signature,
)
import app.routers.papers as papers_module


def test_download_paper_success():
    """Verify valid download flow: decrypts, verifies hash & RSA signature, streams bytes."""
    async def _run():
        original_content = b"%PDF-1.4 Question Paper Secret Content 12345"
        paper_hash = sha256_hash(original_content)
        signature = sign_data(original_content)
        encrypted_blob = aes_encrypt(original_content)

        fake_paper = {
            "id": "paper-123",
            "title": "Mathematics Final",
            "subject": "Math",
            "exam_centre": "Centre-Mumbai-01",
            "setter_id": "setter-1",
            "status": ApprovalStatus.approved,
            "sha256_hash": paper_hash,
            "signature": signature,
            "encrypted_blob": encrypted_blob,
            "unlock_time": datetime.now(timezone.utc),
        }

        exam_centre_user = {
            "sub": "centre-user-1",
            "role": "examination_centre",
            "name": "Centre Admin",
            "institution": "Centre-Mumbai-01",
        }

        mock_papers_coll = AsyncMock()
        mock_papers_coll.find_one.return_value = fake_paper

        with patch.object(type(papers_module.database), "papers", new_callable=PropertyMock, return_value=mock_papers_coll), \
             patch("app.routers.papers.record_audit_log", new_callable=AsyncMock) as mock_audit:

            response = await download_paper(paper_id="paper-123", user=exam_centre_user)

            # Consume streaming response
            downloaded_bytes = b"".join([chunk async for chunk in response.body_iterator])

            assert downloaded_bytes == original_content, "Downloaded bytes must match original content bit-for-bit"
            assert response.headers["content-disposition"] == 'attachment; filename="Mathematics_Final.pdf"'

            # Check audit log was recorded
            mock_audit.assert_called_once()
            audit_kwargs = mock_audit.call_args.kwargs
            assert audit_kwargs["action"] == "DOWNLOAD_PAPER"
            assert audit_kwargs["status"] == "SUCCESS"
            assert audit_kwargs["paper_id"] == "paper-123"

    asyncio.run(_run())


def test_download_paper_tampered_hash_fails():
    """Verify that tampering with the paper hash triggers 409 and TAMPER_DETECTED audit log."""
    async def _run():
        original_content = b"Original exam content"
        signature = sign_data(original_content)
        encrypted_blob = aes_encrypt(original_content)

        fake_paper = {
            "id": "paper-tampered",
            "title": "Physics",
            "exam_centre": "Centre-01",
            "status": ApprovalStatus.approved,
            "sha256_hash": "tampered_fake_hash_000000000000000000000000000000000000000000000",
            "signature": signature,
            "encrypted_blob": encrypted_blob,
            "unlock_time": datetime.now(timezone.utc),
        }

        admin_user = {"sub": "admin-1", "role": "administrator", "name": "Admin"}

        mock_papers_coll = AsyncMock()
        mock_papers_coll.find_one.return_value = fake_paper

        with patch.object(type(papers_module.database), "papers", new_callable=PropertyMock, return_value=mock_papers_coll), \
             patch("app.routers.papers.record_audit_log", new_callable=AsyncMock) as mock_audit:

            with pytest.raises(HTTPException) as exc_info:
                await download_paper(paper_id="paper-tampered", user=admin_user)

            assert exc_info.value.status_code == 409
            assert "Integrity verification failed" in exc_info.value.detail

            mock_audit.assert_called_once()
            assert mock_audit.call_args.kwargs["action"] == "TAMPER_DETECTED"
            assert mock_audit.call_args.kwargs["status"] == "FAILED"

    asyncio.run(_run())


def test_download_paper_bad_signature_fails():
    """Verify that an invalid/corrupted RSA signature triggers 409 and TAMPER_DETECTED audit log."""
    async def _run():
        original_content = b"Original exam content"
        paper_hash = sha256_hash(original_content)
        encrypted_blob = aes_encrypt(original_content)

        fake_paper = {
            "id": "paper-bad-sig",
            "title": "Chemistry",
            "exam_centre": "Centre-01",
            "status": ApprovalStatus.approved,
            "sha256_hash": paper_hash,
            "signature": "corrupted_invalid_signature_base64",
            "encrypted_blob": encrypted_blob,
            "unlock_time": datetime.now(timezone.utc),
        }

        admin_user = {"sub": "admin-1", "role": "administrator", "name": "Admin"}

        mock_papers_coll = AsyncMock()
        mock_papers_coll.find_one.return_value = fake_paper

        with patch.object(type(papers_module.database), "papers", new_callable=PropertyMock, return_value=mock_papers_coll), \
             patch("app.routers.papers.record_audit_log", new_callable=AsyncMock) as mock_audit:

            with pytest.raises(HTTPException) as exc_info:
                await download_paper(paper_id="paper-bad-sig", user=admin_user)

            assert exc_info.value.status_code == 409
            assert "Authenticity verification failed" in exc_info.value.detail

            mock_audit.assert_called_once()
            assert mock_audit.call_args.kwargs["action"] == "TAMPER_DETECTED"

    asyncio.run(_run())


def test_download_paper_unapproved_or_locked():
    """Verify that download fails if paper is not approved or not unlocked."""
    async def _run():
        original_content = b"Content"
        fake_paper = {
            "id": "paper-pending",
            "title": "History",
            "exam_centre": "Centre-01",
            "status": ApprovalStatus.pending,
            "sha256_hash": sha256_hash(original_content),
            "signature": sign_data(original_content),
            "encrypted_blob": aes_encrypt(original_content),
            "unlock_time": None,
        }

        admin_user = {"sub": "admin-1", "role": "administrator", "name": "Admin"}

        mock_papers_coll = AsyncMock()
        mock_papers_coll.find_one.return_value = fake_paper

        with patch.object(type(papers_module.database), "papers", new_callable=PropertyMock, return_value=mock_papers_coll):
            # Not approved
            with pytest.raises(HTTPException) as exc_info:
                await download_paper(paper_id="paper-pending", user=admin_user)
            assert exc_info.value.status_code == 403
            assert "not been approved" in exc_info.value.detail

            # Approved but not unlocked
            fake_paper["status"] = ApprovalStatus.approved
            with pytest.raises(HTTPException) as exc_info:
                await download_paper(paper_id="paper-pending", user=admin_user)
            assert exc_info.value.status_code == 403
            assert "must be unlocked before download" in exc_info.value.detail

    asyncio.run(_run())


def test_download_paper_centre_scoping():
    """Verify that an unauthorized centre is rejected with 403."""
    async def _run():
        original_content = b"Content"
        fake_paper = {
            "id": "paper-centre-scoped",
            "title": "English",
            "exam_centre": "Assigned-Centre-A",
            "status": ApprovalStatus.approved,
            "sha256_hash": sha256_hash(original_content),
            "signature": sign_data(original_content),
            "encrypted_blob": aes_encrypt(original_content),
            "unlock_time": datetime.now(timezone.utc),
        }

        wrong_centre_user = {
            "sub": "user-other-centre",
            "role": "examination_centre",
            "name": "Other Centre",
            "institution": "Assigned-Centre-B",
        }

        mock_papers_coll = AsyncMock()
        mock_papers_coll.find_one.return_value = fake_paper

        with patch.object(type(papers_module.database), "papers", new_callable=PropertyMock, return_value=mock_papers_coll):
            with pytest.raises(HTTPException) as exc_info:
                await download_paper(paper_id="paper-centre-scoped", user=wrong_centre_user)

            assert exc_info.value.status_code == 403
            assert "not assigned to your centre" in exc_info.value.detail

    asyncio.run(_run())
