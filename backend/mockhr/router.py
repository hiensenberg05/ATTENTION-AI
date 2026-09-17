"""HTTP routes for the mock internal HR application.

Mounted under `/mock-hr` on the same uvicorn process as the platform API, but it
is a genuinely separate application: server-rendered HTML, its own mutable store,
no shared session, and nothing about it is imported by the decision layer. The
executor reaches it the only way a real target system could be reached - over
HTTP, through a browser.

EVERY INTERACTIVE ELEMENT CARRIES A `data-testid`. That is the contract with the
Playwright executor, which locates elements by stable test ids and never by
coordinates, visual position, or text that a translation could change. The ids
this app renders are the ones declared in `execution/screens.py`; if the two ever
drift apart, the browser tests fail loudly.

Both screens mirror what was directly observed in the Dataset B screenshots
(`phase2/results/visual_audit.md`):

    /leave-applications  管理ID / 社員ID / 氏名 / 申請種別 / 期間 / 所属部署 /
                         ステータス, a 参照 note carrying 事前承認要否, a
                         承認コメント box, and the 承認 / 差戻し controls.
    /payroll-items       管理ID / 社員ID / 氏名 / 区分 / 金額 / ステータス, a 参照
                         note carrying 申請者区分 / 承認権限, a 処理コメント box,
                         and the 登録確定 / 保留 controls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.common import LeaveStatus, PayrollStatus

from .store import ActionNotAllowed, RecordNotFound, leave_store, payroll_store

BASE_PATH = "/mock-hr"

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

router = APIRouter(prefix=BASE_PATH, tags=["mock-hr"])

_STATUS_CLASS = {
    LeaveStatus.PENDING.value: "status-pending",
    LeaveStatus.APPROVED.value: "status-approved",
    LeaveStatus.RETURNED.value: "status-returned",
    PayrollStatus.UNPROCESSED.value: "status-pending",
    PayrollStatus.CONFIRMED.value: "status-approved",
    PayrollStatus.ON_HOLD.value: "status-returned",
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


def _not_found(record_id: str) -> HTMLResponse:
    return HTMLResponse(
        f'<main data-testid="not-found">該当する記録が見つかりません: {record_id}</main>',
        status_code=404,
    )


@router.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(f"{BASE_PATH}/leave-applications", status_code=302)


# ---------------------------------------------------------------------------
# 休暇申請 (Leave Approval)
# ---------------------------------------------------------------------------


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
        context=_context(request, records=leave_store.all(), flash=flash),
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
        record = leave_store.get(record_id)
    except RecordNotFound:
        return _not_found(record_id)

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
        updated = leave_store.apply_action(record_id, action, comment.strip() or None)
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


# ---------------------------------------------------------------------------
# 経費精算・給与変更 (Payroll Confirmation)
# ---------------------------------------------------------------------------


@router.get("/payroll-items", response_class=HTMLResponse)
def payroll_list(request: Request, flash: Optional[str] = None) -> HTMLResponse:
    """経費精算・給与変更一覧 - the payroll queue screen, and the verification target."""
    return TEMPLATES.TemplateResponse(
        request=request,
        name="payroll_list.html",
        context=_context(request, records=payroll_store.all(), flash=flash),
    )


@router.get("/payroll-items/{record_id}", response_class=HTMLResponse)
def payroll_detail(
    request: Request,
    record_id: str,
    flash: Optional[str] = None,
    error: Optional[str] = None,
) -> HTMLResponse:
    """経費精算詳細 - the detail panel, with 登録確定 / 保留."""
    try:
        record = payroll_store.get(record_id)
    except RecordNotFound:
        return _not_found(record_id)

    return TEMPLATES.TemplateResponse(
        request=request,
        name="payroll_detail.html",
        context=_context(
            request,
            record=record,
            actionable=record.status is PayrollStatus.UNPROCESSED,
            flash=flash,
            error=error,
        ),
    )


@router.post("/payroll-items/{record_id}/action", response_class=HTMLResponse)
def payroll_action(
    record_id: str,
    action: str = Form(...),
    comment: str = Form(default=""),
) -> RedirectResponse:
    """登録確定 / 保留 submission, POST-redirect-GET as above."""
    if action not in ("approve", "reject"):
        return RedirectResponse(
            f"{BASE_PATH}/payroll-items/{record_id}?error=unknown+action",
            status_code=303,
        )

    try:
        updated = payroll_store.apply_action(record_id, action, comment.strip() or None)
    except RecordNotFound:
        return RedirectResponse(f"{BASE_PATH}/payroll-items", status_code=303)
    except ActionNotAllowed as exc:
        return RedirectResponse(
            f"{BASE_PATH}/payroll-items/{record_id}?error={exc}", status_code=303
        )

    label = "登録確定" if action == "approve" else "保留"
    return RedirectResponse(
        f"{BASE_PATH}/payroll-items/{record_id}"
        f"?flash={label}しました。ステータス: {updated.status.value}",
        status_code=303,
    )
