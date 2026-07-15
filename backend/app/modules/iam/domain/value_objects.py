import re
from enum import Enum
from app.shared.exceptions import DamaBoxDomainException

class RoleType(str, Enum):
    OWNER = "Owner"
    ADMIN = "Admin"
    MEMBER = "Member"
    GUEST = "Guest"

class Email:
    EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

    def __init__(self, value: str):
        cleaned = value.strip().lower()
        if not self.EMAIL_REGEX.match(cleaned):
            raise DamaBoxDomainException(
                detail=f"Formato de e-mail inválido: '{value}'",
                title="Validação de E-mail"
            )
        self._value = cleaned

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"Email('{self._value}')"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Email):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other.strip().lower()
        return False

    def __hash__(self) -> int:
        return hash(self._value)
