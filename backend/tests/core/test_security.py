import time
import pytest
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

def test_password_hashing_and_verification():
    raw_password = "MinhaSenhaSegura#2026!"
    hashed = get_password_hash(raw_password)
    
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("SenhaErrada123", hashed) is False

def test_jwt_generation_and_decoding():
    payload = {
        "sub": "01908000-0000-7000-8000-000000000001",
        "email": "davi@dama.com",
        "cid": "01908000-0000-7000-8000-000000000015",
        "role": "Owner"
    }
    
    token = create_access_token(payload, expires_delta_minutes=10)
    assert isinstance(token, str)
    assert len(token) > 20
    
    decoded = decode_access_token(token)
    assert decoded["sub"] == payload["sub"]
    assert decoded["email"] == payload["email"]
    assert decoded["cid"] == payload["cid"]
    assert decoded["role"] == payload["role"]
    assert "exp" in decoded

def test_expired_jwt_raises_error():
    payload = {"sub": "test-user"}
    token = create_access_token(payload, expires_delta_minutes=-1) # Já expirado
    
    with pytest.raises(ValueError, match="Token expirado ou inválido"):
        decode_access_token(token)
