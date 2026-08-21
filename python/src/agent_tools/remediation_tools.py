"""Approval-gated remediation proposals with no database execution capability."""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROPOSAL_STORE_PATH = PROJECT_ROOT / "runtime" / "remediation_proposals.json"

_STORE_LOCK = threading.Lock()
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_ALLOWED_FIELDS = {
    "customers": {"email", "city", "signup_date"},
    "orders": {"customer_id", "order_date", "order_status"},
    "products": {"product_name", "category", "price"},
    "order_items": {"order_id", "product_id", "quantity"},
}
_ID_FIELDS = {
    "customers": "customer_id",
    "orders": "order_id",
    "products": "product_id",
    "order_items": "order_item_id",
}


def _error(action: str, message: str) -> dict[str, Any]:
    return {"status": "error", "action": action, "message": message}


def _load_store() -> dict[str, Any]:
    if not PROPOSAL_STORE_PATH.exists():
        return {"version": 1, "proposals": []}
    return json.loads(PROPOSAL_STORE_PATH.read_text(encoding="utf-8"))


def _save_store(store: dict[str, Any]) -> None:
    PROPOSAL_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = PROPOSAL_STORE_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(store, indent=2, default=str),
        encoding="utf-8",
    )
    temporary_path.replace(PROPOSAL_STORE_PATH)


def _find_proposal(store: dict[str, Any], proposal_id: str):
    return next(
        (
            proposal
            for proposal in store.get("proposals", [])
            if proposal.get("proposal_id") == proposal_id
        ),
        None,
    )


def create_remediation_proposal(
    source_table: str,
    record_id: str,
    field_name: str,
    proposed_value: str,
    reason: str,
) -> dict[str, Any]:
    """Create a pending source-data fix proposal; this never changes data."""
    normalized_table = str(source_table).strip().lower()
    normalized_field = str(field_name).strip().lower()
    normalized_record_id = str(record_id).strip()
    if normalized_table not in _ALLOWED_FIELDS:
        return _error("create proposal", "source_table is not allowlisted.")
    if normalized_field not in _ALLOWED_FIELDS[normalized_table]:
        return _error(
            "create proposal",
            f"field_name is not allowlisted for {normalized_table}.",
        )
    if not _IDENTIFIER_PATTERN.fullmatch(normalized_record_id):
        return _error("create proposal", "record_id contains invalid characters.")
    if not str(reason).strip():
        return _error("create proposal", "reason is required.")
    if len(str(proposed_value)) > 200 or len(str(reason)) > 500:
        return _error("create proposal", "proposal text is too long.")

    proposal = {
        "proposal_id": uuid.uuid4().hex,
        "status": "pending_approval",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_table": normalized_table,
        "id_field": _ID_FIELDS[normalized_table],
        "record_id": normalized_record_id,
        "field_name": normalized_field,
        "proposed_value": str(proposed_value),
        "reason": str(reason).strip(),
        "execution_status": "not_executed",
    }
    with _STORE_LOCK:
        store = _load_store()
        store["proposals"].append(proposal)
        _save_store(store)
    return {"status": "success", "proposal": proposal}


def approve_remediation_proposal(
    proposal_id: str,
    approved_by: str,
    confirmation: bool = False,
) -> dict[str, Any]:
    """Record explicit human approval; this still never changes source data."""
    if confirmation is not True:
        return _error(
            "approve proposal",
            "confirmation must be true for explicit human approval.",
        )
    if not str(approved_by).strip():
        return _error("approve proposal", "approved_by is required.")

    with _STORE_LOCK:
        store = _load_store()
        proposal = _find_proposal(store, proposal_id)
        if proposal is None:
            return _error("approve proposal", "proposal_id was not found.")
        if proposal["status"] != "pending_approval":
            return _error(
                "approve proposal",
                f"proposal is already {proposal['status']}.",
            )
        proposal["status"] = "approved"
        proposal["approved_by"] = str(approved_by).strip()[:100]
        proposal["approved_at"] = datetime.now(timezone.utc).isoformat()
        proposal["execution_status"] = "awaiting_manual_execution"
        _save_store(store)
    return {"status": "success", "proposal": proposal}


def reject_remediation_proposal(
    proposal_id: str,
    rejected_by: str,
    reason: str,
) -> dict[str, Any]:
    """Reject a pending proposal without changing source data."""
    if not str(rejected_by).strip() or not str(reason).strip():
        return _error(
            "reject proposal",
            "rejected_by and reason are required.",
        )
    with _STORE_LOCK:
        store = _load_store()
        proposal = _find_proposal(store, proposal_id)
        if proposal is None:
            return _error("reject proposal", "proposal_id was not found.")
        if proposal["status"] != "pending_approval":
            return _error(
                "reject proposal",
                f"proposal is already {proposal['status']}.",
            )
        proposal["status"] = "rejected"
        proposal["rejected_by"] = str(rejected_by).strip()[:100]
        proposal["rejection_reason"] = str(reason).strip()[:500]
        proposal["rejected_at"] = datetime.now(timezone.utc).isoformat()
        _save_store(store)
    return {"status": "success", "proposal": proposal}


def get_remediation_proposal(proposal_id: str) -> dict[str, Any]:
    """Return one locally stored remediation proposal by ID."""
    with _STORE_LOCK:
        proposal = _find_proposal(_load_store(), proposal_id)
    if proposal is None:
        return _error("read proposal", "proposal_id was not found.")
    return {"status": "success", "proposal": proposal}


def get_approved_remediation_script(proposal_id: str) -> dict[str, Any]:
    """Return parameterized MySQL SQL only after approval; never execute it."""
    with _STORE_LOCK:
        proposal = _find_proposal(_load_store(), proposal_id)
    if proposal is None:
        return _error("build remediation script", "proposal_id was not found.")
    if proposal["status"] != "approved":
        return _error(
            "build remediation script",
            "proposal must be approved before a script is available.",
        )
    sql = (
        f"UPDATE {proposal['source_table']} "
        f"SET {proposal['field_name']} = %s "
        f"WHERE {proposal['id_field']} = %s;"
    )
    return {
        "status": "success",
        "proposal_id": proposal_id,
        "execution": "manual_only",
        "sql": sql,
        "parameters": [proposal["proposed_value"], proposal["record_id"]],
        "warning": "Review and execute this against MySQL manually, then rerun ETL.",
    }
