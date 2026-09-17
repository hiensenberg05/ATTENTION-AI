"""HTTP routes for the mock internal HR application.

Mounted under `/mock-hr` on the same uvicorn process as the platform API, but it
is a genuinely separate application: server-rendered HTML, its own mutable store,
no shared session, and nothing about it is imported by the decision layer. The
executor reaches it the only way a real target system could be reached - over
HTTP, through a browser.

EVERY INTERACTIVE ELEMENT CARRIES A `data-testid`. That is the contract with the
Playwright executor: it locates elements by stable test ids, never by coordinates,
never by visual position, and never by text that a translation could change.

The screen layout mirrors what was directly observed in the Dataset B screenshots
(`phase2_dataset_b/visual_audit.md`): a list of pending applications, a detail
panel with the 管理ID / 社員ID / 氏名 / 申請種別 / 期間 / 所属部署 / ステータス
fields, a 参照 note carrying 事前承認要否, a free-text 承認コメント box, and the
承認 / 差戻し controls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.common import LeaveStatus

from .store import ActionNotAllowed, RecordNotFound, store

BASE_PATH = "/mock-hr"

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

router = APIRouter(prefix=BASE_PATH, tags=["mock-hr"])

_STATUS_CLASS = {
    LeaveStatus.PENDING.value: "status-pending",
    LeaveStatus.APPROVED.value: "status-approved",
    LeaveStatus.RETURNED.value: "status-returned",
}


def _status_class(value: str) -> str:
    return _STATUS_CLASS.get(value, "")


def _context(request: Request, **extra: object) -> dict[str, object]:
    return {
        "request": request,
        "base": BASE_PATH,
        "status_class": _status_class,
        **extra,
    }


@router.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(f"{BASE_PATH}/leave-applications", status_code=302)


@router.get("/leave-applications", response_class=HTMLResponse)
def leave_list(request: Request, flash: Optional[str] = None) -> HTMLResponse:
    """休暇申請一覧 - the queue screen.

    This is also the page the verification step re-reads. Verifying against the
    list rather than the detail page the action was submitted from makes the
    re-read genuinely independent of the page that performed the action.
    """
    return TEMPLATES.TemplateResponse(
        request=request,
        name="leave_list.html",
        context=_context(request, records=store.all(), flash=flash),
    )


@router.get("/leave-applications/{record_id}", response_class=HTMLResponse)
def leave_detail(
    request: Request,
    record_id: str,
    flash: Optional[str] = None,
    error: Optional[str] = None,
) -> HTMLResponse:
    """休暇申請詳細 - the detail panel, with the action controls."""
    try:
        record = store.get(record_id)
    except RecordNotFound:
        return HTMLResponse(
            f'<main data-testid="not-found">該当する申請が見つかりません: {record_id}</main>',
            status_code=404,
        )

    return TEMPLATES.TemplateResponse(
        request=request,
        name="leave_detail.html",
        context=_context(
            request,
            record=record,
            actionable=record.status is LeaveStatus.PENDING,
            flash=flash,
            error=error,
        ),
    )


@router.post("/leave-applications/{record_id}/action", response_class=HTMLResponse)
def leave_action(
    record_id: str,
    action: str = Form(...),
    comment: str = Form(default=""),
) -> RedirectResponse:
    """承認 / 差戻し submission.

    POST-redirect-GET, so the result is a normal page load the executor and a
    human both observe the same way, and so a refresh cannot replay the action.
    """
    if action not in ("approve", "reject"):
        return RedirectResponse(
            f"{BASE_PATH}/leave-applications/{record_id}?error=unknown+action",
            status_code=303,
        )

    try:
        updated = store.apply_action(record_id, action, comment.strip() or None)
    except RecordNotFound:
        return RedirectResponse(f"{BASE_PATH}/leave-applications", status_code=303)
    except ActionNotAllowed as exc:
        return RedirectResponse(
            f"{BASE_PATH}/leave-applications/{record_id}?error={exc}", status_code=303
        )

    label = "承認" if action == "approve" else "差戻し"
    return RedirectResponse(
        f"{BASE_PATH}/leave-applications/{record_id}"
        f"?flash={label}しました。ステータス: {updated.status.value}",
        status_code=303,
    )
