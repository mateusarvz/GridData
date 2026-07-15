from enum import Enum
from typing import Dict, Any

class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REVERT = "revert"

class ChangeDiff:
    def __init__(self, changes: Dict[str, Dict[str, Any]]):
        self.changes = changes

    @classmethod
    def compute(cls, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> "ChangeDiff":
        changes = {}
        all_keys = set(old_data.keys()) | set(new_data.keys())
        for key in all_keys:
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            if old_val != new_val:
                changes[key] = {"old": old_val, "new": new_val}
        return cls(changes)

    @staticmethod
    def revert(current_data: Dict[str, Any], diff_changes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Reverte as mudanças aplicando o valor 'old' de cada campo alterado.
        Se 'old' era None (campo não existia antes), remove o chave.
        """
        reverted = current_data.copy()
        for key, change in diff_changes.items():
            old_val = change.get("old")
            if old_val is None:
                reverted.pop(key, None)
            else:
                reverted[key] = old_val
        return reverted
