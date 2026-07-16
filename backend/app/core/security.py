import time
from typing import Any, Dict
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from app.core.config import settings

ph = PasswordHasher()

def get_password_hash(password: str) -> str:
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False

def create_access_token(data: Dict[str, Any], expires_delta_minutes: int | None = None) -> str:
    to_encode = data.copy()
    if expires_delta_minutes is not None:
        expire = int(time.time()) + (expires_delta_minutes * 60)
    else:
        expire = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expirado ou inválido")
    except jwt.InvalidTokenError:
        raise ValueError("Token expirado ou inválido")
