from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequestDTO(BaseModel):
    email: str
    password: str

class TokenResponseDTO(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    company_id: Optional[str] = None
    database_name: Optional[str] = None
    role: Optional[str] = None

class SwitchTenantDTO(BaseModel):
    target_company_id: str
