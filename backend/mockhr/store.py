"""Mutable state for the mock internal HR application.

WHY THIS EXISTS SEPARATELY FROM `repository`: `repository` is the read-only loader
for the seed JSON. This module is the mock HR system's own system of record - the
thing whose status actually changes when a button is clicked, and the thing the
verification step independently re-reads afterwards.

That separation is the point of the whole prototype. The executor does not tell
the platform "I confirmed it"; it clicks a control in a system it does not own,
and then a second, independent read against that same system decides whether
anything really happened.

ONE STORE CLASS, TWO QUEUES. Leave requests and payroll items behave identically
as far as the mock system is concerned - a record is pending, an action moves it
to one of two terminal labels, and it cannot be actioned twice - so the behaviour
lives in one generic class parameterised by the status labels. Adding a third
queue is a `RecordStore(...)` call, not another class.

In-memory on purpose. The demo must be repeatable, so `reset()` restores the seed
and the process holds no durable state.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable, Generic, Literal, Optional, Sequence, TypeVar

import repository
from models.common import LeaveStatus, PayrollStatus
from models.leave import LeaveRequest
from models.payroll import PayrollItem

Action = Literal["approve", "reject"]

R = TypeVar("R", LeaveRequest, PayrollItem)


class RecordNotFound(KeyError):
    """The mock HR system has no record with that 管理ID."""


class ActionNotAllowed(RuntimeError):
    """The record is not in a state where this action means anything."""


class ActionLogEntry:
    """One action the mock HR system recorded, for the demo's own audit panel."""

    __slots__ = (
        "queue",
        "record_id",
        "action",
        "status_before",
        "status_after",
        "comment",
        "at",
    )

    def __init__(
        self,
        queue: str,
        record_id: str,
        action: Action,
        status_before: str,
        status_after: str,
        comment: Optional[str],
    ) -> None:
        self.queue = queue
        self.record_id = record_id
        self.action = action
        self.status_before = status_before
        self.status_after = status_after
        self.comment = comment
        self.at = datetime.now(timezone.utc)

    def as_dict(self) -> dict[str, object]:
        return {
            "queue": self.queue,
            "record_id": self.record_id,
            "action": self.action,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "comment": self.comment,
            "at": self.at.isoformat(),
        }


class RecordStore(Generic[R]):
    """One mutable queue of business records inside the mock HR system."""

    def __init__(
        self,
        queue: str,
        seed: Callable[[], Sequence[R]],
        pending_status: object,
        positive_status: object,
        negative_status: object,
    ) -> None:
        self.queue = queue
        self._seed = seed
        self._pending = pending_status
        #: Both post-action labels are PROTOTYPE ASSUMPTIONS - no processed record
        #: was ever captured in Dataset B, only the button labels were.
        self._result = {"approve": positive_status, "reject": negative_status}
        self._lock = threading.RLock()
        self._records: dict[str, R] = {}
        self._log: list[ActionLogEntry] = []
        self.reset()

    def reset(self) -> None:
        """Restore the seed data and clear the action log.

        Records are deep-copied out of the repository cache so that mutating the
        mock HR system can never corrupt the read-only seed the rest of the
        backend shares.
        """
        with self._lock:
            self._records = {r.record_id: r.model_copy(deep=True) for r in self._seed()}
            self._log = []

    def all(self) -> list[R]:
        """Every record, in seed order."""
        with self._lock:
            return [r.model_copy(deep=True) for r in self._records.values()]

    def get(self, record_id: str) -> R:
        """One record by 管理ID, or raise RecordNotFound."""
        with self._lock:
            record = self._records.get(record_id)
            if record is None:
                raise RecordNotFound(record_id)
            return record.model_copy(deep=True)

    def apply_action(
        self, record_id: str, action: Action, comment: Optional[str] = None
    ) -> R:
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

            if record.status is not self._pending:
                raise ActionNotAllowed(
                    f"{record_id} is {record.status.value}; only "
                    f"{self._pending.value} records can be actioned."  # type: ignore[attr-defined]
                )

            before = record.status
            updated = record.model_copy(
                deep=True,
                update={
                    "status": self._result[action],
                    "comment": comment or record.comment,
                },
            )
            self._records[record_id] = updated
            self._log.append(
                ActionLogEntry(
                    queue=self.queue,
                    record_id=record_id,
                    action=action,
                    status_before=before.value,
                    status_after=updated.status.value,
                    comment=comment,
                )
            )
            return updated.model_copy(deep=True)

    def action_log(self) -> list[dict[str, object]]:
        """Everything this queue has been asked to do, oldest first."""
        with self._lock:
            return [entry.as_dict() for entry in self._log]


#: Process-wide singletons. The mock HR system is one system; there is one of it.
leave_store: RecordStore[LeaveRequest] = RecordStore(
    queue="leave-applications",
    seed=repository.get_leave_requests,
    pending_status=LeaveStatus.PENDING,
    positive_status=LeaveStatus.APPROVED,
    negative_status=LeaveStatus.RETURNED,
)

payroll_store: RecordStore[PayrollItem] = RecordStore(
    queue="payroll-items",
    seed=repository.get_payroll_items,
    pending_status=PayrollStatus.UNPROCESSED,
    positive_status=PayrollStatus.CONFIRMED,
    negative_status=PayrollStatus.ON_HOLD,
)

#: Backwards-compatible alias - `store` meant the leave queue before payroll existed.
store = leave_store

ALL_STORES: tuple[RecordStore, ...] = (leave_store, payroll_store)


def reset_all() -> None:
    """Restore every queue, so the demo can be re-run from a clean state."""
    for s in ALL_STORES:
        s.reset()


def combined_action_log() -> list[dict[str, object]]:
    """Every action across every queue, oldest first."""
    entries = [e for s in ALL_STORES for e in s.action_log()]
    return sorted(entries, key=lambda e: str(e["at"]))
