"""Mutable state for the mock internal HR application.

WHY THIS EXISTS SEPARATELY FROM `repository`: `repository` is the read-only loader
for the seed JSON. This module is the mock HR system's own system of record - the
thing whose status actually changes when a button is clicked, and the thing the
verification step independently re-reads afterwards.

That separation is the point of the whole prototype. The executor does not tell
the platform "I approved it"; it clicks a control in a system it does not own, and
then a second, independent read against that same system decides whether anything
really happened.

In-memory on purpose. The demo must be repeatable, so `reset()` restores the seed
and the process holds no durable state.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Literal, Optional

import repository
from models.common import LeaveStatus
from models.leave import LeaveRequest

Action = Literal["approve", "reject"]

#: What each action does to a record's status. Both post-action labels are
#: PROTOTYPE ASSUMPTIONS - no approved or returned record was ever captured in
#: Dataset B, only the button labels were. See `models.common.LeaveStatus`.
ACTION_RESULT: dict[Action, LeaveStatus] = {
    "approve": LeaveStatus.APPROVED,
    "reject": LeaveStatus.RETURNED,
}

#: Only a pending record can be acted on, mirroring the real screen where the
#: action buttons are only meaningful on a 申請中 row.
ACTIONABLE_STATUS = LeaveStatus.PENDING


class RecordNotFound(KeyError):
    """The mock HR system has no record with that 管理ID."""


class ActionNotAllowed(RuntimeError):
    """The record is not in a state where this action means anything."""


class ActionLogEntry:
    """One action the mock HR system recorded, for the demo's own audit panel."""

    __slots__ = ("record_id", "action", "status_before", "status_after", "comment", "at")

    def __init__(
        self,
        record_id: str,
        action: Action,
        status_before: str,
        status_after: str,
        comment: Optional[str],
    ) -> None:
        self.record_id = record_id
        self.action = action
        self.status_before = status_before
        self.status_after = status_after
        self.comment = comment
        self.at = datetime.now(timezone.utc)

    def as_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "action": self.action,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "comment": self.comment,
            "at": self.at.isoformat(),
        }


class LeaveStore:
    """The mock HR system's live leave-application table."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, LeaveRequest] = {}
        self._log: list[ActionLogEntry] = []
        self.reset()

    def reset(self) -> None:
        """Restore the seed data and clear the action log.

        Records are deep-copied out of the repository cache so that mutating the
        mock HR system can never corrupt the read-only seed the rest of the
        backend shares.
        """
        with self._lock:
            self._records = {
                r.record_id: r.model_copy(deep=True)
                for r in repository.get_leave_requests()
            }
            self._log = []

    def all(self) -> list[LeaveRequest]:
        """Every record, in seed order."""
        with self._lock:
            return [r.model_copy(deep=True) for r in self._records.values()]

    def get(self, record_id: str) -> LeaveRequest:
        """One record by 管理ID, or raise RecordNotFound."""
        with self._lock:
            record = self._records.get(record_id)
            if record is None:
                raise RecordNotFound(record_id)
            return record.model_copy(deep=True)

    def apply_action(
        self, record_id: str, action: Action, comment: Optional[str] = None
    ) -> LeaveRequest:
        """Perform an action on a record and return its new state.

        Raises ActionNotAllowed if the record is not pending. That refusal is
        deliberate: it gives the executor something real to fail against, so the
        "clicking is not the same as succeeding" distinction can actually be
        demonstrated rather than merely asserted.
        """
        with self._lock:
            record = self._records.get(record_id)
            if record is None:
                raise RecordNotFound(record_id)

            if record.status is not ACTIONABLE_STATUS:
                raise ActionNotAllowed(
                    f"{record_id} is {record.status.value}; only "
                    f"{ACTIONABLE_STATUS.value} records can be actioned."
                )

            before = record.status
            updated = record.model_copy(
                deep=True,
                update={
                    "status": ACTION_RESULT[action],
                    "comment": comment or record.comment,
                },
            )
            self._records[record_id] = updated
            self._log.append(
                ActionLogEntry(
                    record_id=record_id,
                    action=action,
                    status_before=before.value,
                    status_after=updated.status.value,
                    comment=comment,
                )
            )
            return updated.model_copy(deep=True)

    def action_log(self) -> list[dict[str, object]]:
        """Everything the mock HR system has been asked to do, oldest first."""
        with self._lock:
            return [entry.as_dict() for entry in self._log]


#: Process-wide singleton. The mock HR system is one system; there is one of it.
store = LeaveStore()
