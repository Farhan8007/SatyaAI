"""
JWT issuing/verification and password hashing (bcrypt via passlib).

Day 2 changes (Security Lead):
- get_current_user now re-fetches from MongoDB on every request, rejecting
  suspended / deleted users immediately instead of trusting the JWT payload
  until it expires.
- Added require_paper_access() for subject/centre scoping (papers.py Day 3).
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.database import database

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Decode the JWT, then verify the user still exists and is active in the DB.

    Returns a dict with the same keys routers already expect:
    ``sub`` (user id), ``role``, ``name``.
    """
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # ---- Day 2: DB re-fetch on every request ----
    user_doc = await database.users.find_one({"id": user_id})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User no longer exists")
    if not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=403,
            detail="This account has been suspended. Contact your Administrator.",
        )

    # Return a dict that keeps backward compatibility with existing routers
    # (they read user["sub"], user["role"], user["name"]).
    return {
        "sub": user_doc["id"],
        "role": user_doc["role"],
        "name": user_doc["name"],
        "institution": user_doc.get("institution"),
    }


def require_roles(*allowed_roles: str):
    """FastAPI dependency factory for role-based access control."""

    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions for this action")
        return user

    return checker


# ---------------------------------------------------------------------------
# Day 2: Subject/centre scoping helpers (used by papers.py starting Day 3)
# ---------------------------------------------------------------------------

def require_paper_access(*, owner_field: str = "setter_id", centre_field: str = "exam_centre"):
    """Dependency factory that verifies the caller owns or is assigned to a paper.

    Rules:
    - Administrators bypass all scoping checks.
    - Paper setters may only access papers where ``paper[owner_field]``
      matches their user id.
    - Examination centres may only access papers where
      ``paper[centre_field]`` matches their institution or user id.
    - All other roles are denied (403).

    The caller injects this *after* fetching the paper document and passes it
    via the ``paper`` keyword argument::

        @router.get("/{paper_id}/download")
        async def download(paper_id: str,
                           user = Depends(get_current_user)):
            paper = await database.papers.find_one({"id": paper_id})
            verify_paper_access(user, paper)  # raises 403 if denied
    """
    async def _verify(user: dict, paper: dict | None) -> None:
        if paper is None:
            raise HTTPException(status_code=404, detail="Paper not found")

        role = user.get("role")
        uid = user.get("sub")

        # Administrators can see everything
        if role == "administrator":
            return

        if role == "paper_setter":
            if paper.get(owner_field) != uid:
                raise HTTPException(status_code=403, detail="You can only access your own papers")
            return

        if role == "examination_centre":
            assigned = paper.get(centre_field)
            if assigned is None:
                raise HTTPException(
                    status_code=403,
                    detail="This paper has not been assigned to any examination centre yet",
                )
            # Support both single-value and list-of-centres schemas, matching on ID, institution, or centre name
            allowed_ids = {uid}
            if user.get("institution"):
                allowed_ids.add(user["institution"])
            if user.get("name"):
                allowed_ids.add(user["name"])

            if isinstance(assigned, list):
                if not any(a in allowed_ids for a in assigned):
                    raise HTTPException(status_code=403, detail="This paper is not assigned to your centre")
            else:
                if assigned not in allowed_ids:
                    raise HTTPException(status_code=403, detail="This paper is not assigned to your centre")
            return

        # security_auditor, moderator — grant read-only access by default
        if role in ("security_auditor", "moderator"):
            return

        raise HTTPException(status_code=403, detail="Insufficient permissions for this paper")

    return _verify


# Pre-instantiated default scoping checker for convenience
verify_paper_access = require_paper_access()
