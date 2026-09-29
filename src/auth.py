import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException, status, Depends
from src.database import get_db

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return f"{salt.hex()}:{pwd_hash.hex()}"

def verify_password(stored_password_hash: str, provided_password: str) -> bool:
    try:
        salt_hex, hash_hex = stored_password_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100_000)
        return secrets.compare_digest(expected_hash, pwd_hash)
    except Exception:
        return False

def create_session(user_id: str, custom_token: Optional[str] = None) -> str:
    token = custom_token or secrets.token_hex(24)
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, now_iso)
        )
    return token

def extract_token_from_request(request: Request) -> Optional[str]:
    # 1. Check cookies: 'session' or 'session_token'
    cookie_token = request.cookies.get("session") or request.cookies.get("session_token")
    if cookie_token:
        return cookie_token

    # 2. Check Cookie header manually (e.g. if passed as "session=xyz")
    cookie_header = request.headers.get("Cookie") or request.headers.get("cookie")
    if cookie_header:
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith("session="):
                return part[len("session="):]

    # 3. Check Authorization header: 'Bearer xyz'
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header:
        parts = auth_header.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        elif len(parts) == 1:
            return parts[0]
            
    # 4. Check query param: '?token=xyz'
    return request.query_params.get("token")

def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    token = extract_token_from_request(request)
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute("""
            SELECT u.id, u.username, u.email, u.full_name, u.role, u.created_at, s.token
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,)).fetchone()
        return row

def get_current_user(request: Request) -> Dict[str, Any]:
    user = get_optional_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid session cookie or Bearer token."
        )
    return user

def require_roles(allowed_roles: List[str]):
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        # 'admin' and 'organizer' are interchangeable aliases with full administrative privileges
        user_role = user.get("role")
        norm_user_role = "admin" if user_role in ("admin", "organizer") else user_role
        norm_allowed = ["admin" if r in ("admin", "organizer") else r for r in allowed_roles]
        
        if norm_user_role not in norm_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}, your role: {user_role}"
            )
        return user
    return role_checker
