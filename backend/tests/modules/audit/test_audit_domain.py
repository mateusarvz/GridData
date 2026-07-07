import pytest
from uuid import uuid4
from app.modules.audit.domain.value_objects import ChangeDiff, AuditAction
from app.modules.audit.domain.entities import AuditLog

def test_change_diff_compute():
    old_data = {"nome": "Dama", "status": "Rascunho", "prioridade": 1}
    new_data = {"nome": "Dama Box", "status": "Rascunho", "valor": 500}
    
    diff = ChangeDiff.compute(old_data, new_data)
    assert diff.changes == {
        "nome": {"old": "Dama", "new": "Dama Box"},
        "prioridade": {"old": 1, "new": None},
        "valor": {"old": None, "new": 500}
    }
    assert "status" not in diff.changes

def test_change_diff_reversion():
    current_data = {"nome": "Dama Box", "status": "Rascunho", "valor": 500}
    diff_payload = {
        "nome": {"old": "Dama", "new": "Dama Box"},
        "prioridade": {"old": 1, "new": None},
        "valor": {"old": None, "new": 500}
    }
    
    reverted_data = ChangeDiff.revert(current_data, diff_payload)
    assert reverted_data == {"nome": "Dama", "status": "Rascunho", "prioridade": 1}

def test_audit_log_entity_creation():
    row_id = uuid4()
    table_id = uuid4()
    user_id = uuid4()
    diff = {"status": {"old": "Novo", "new": "Concluído"}}
    
    log = AuditLog.create(
        row_id=row_id,
        table_id=table_id,
        user_id=user_id,
        action=AuditAction.UPDATE,
        version=2,
        diff=diff
    )
    assert log.row_id == row_id
    assert log.action == AuditAction.UPDATE
    assert log.version == 2
    assert log.diff["status"]["old"] == "Novo"
