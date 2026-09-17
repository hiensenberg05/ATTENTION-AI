"""Deterministic browser execution against the mock HR application.

NO LLM IN THIS FILE, AND NO JUDGEMENT IN THIS FILE. By the time anything here
runs, the decision has already been made - either by the policy layer or by a
human in the review queue. This module's entire job is to perform an action that
was already decided, and it has no way to decide anything itself: there is no
branch below that inspects a business field to choose an outcome.

SELECTOR DISCIPLINE. Every element is located by `data-testid`. There is no
coordinate clicking, no "click the third button", no screenshot matching, no
XPath over layout, and no text matching that a translation or a label change would
break. If a test id is missing, the step fails loudly rather than guessing - a
silent mis-click in a real HR system is far worse than a failed run.

TIMING. Playwright waits on element state rather than on the clock; there is no
`sleep` anywhere in this file.
"""

from __future__ import annotations

import logging
import os
from types import TracebackType
from typing import Optional

from playwright.sync_api import (
    Browser,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

logger = logging.getLogger(__name__)

#: Where the mock HR application is served when nothing else is configured.
FALLBACK_BASE_URL = "http://127.0.0.1:8000/mock-hr"

# The three settings below are read from the environment ON EVERY CALL rather than
# captured at import time. Binding them as module-level constants would freeze
# whatever the environment happened to be when this module was first imported,
# which makes `MOCK_HR_BASE_URL` silently ineffective for anything that configures
# itself after startup - including tests that need to point the executor at a
# different server.


def default_base_url() -> str:
    """Where to drive the browser. Override with `MOCK_HR_BASE_URL`."""
    return os.environ.get("MOCK_HR_BASE_URL", FALLBACK_BASE_URL).rstrip("/")


def default_timeout_ms() -> int:
    """Per-action timeout. Override with `PLAYWRIGHT_TIMEOUT_MS`."""
    return int(os.environ.get("PLAYWRIGHT_TIMEOUT_MS", "10000"))


def default_headless() -> bool:
    """Headed mode is genuinely useful in a demo - you can watch the agent work.

    Set `PLAYWRIGHT_HEADLESS=false` to watch it.
    """
    return os.environ.get("PLAYWRIGHT_HEADLESS", "true").lower() != "false"


class ExecutionError(RuntimeError):
    """A browser step could not be completed."""


class LeaveApprovalExecutor:
    """Drives the leave-application screens of the mock HR system.

    Used as a context manager so the browser is always torn down, including when
    a step raises:

        with LeaveApprovalExecutor() as ex:
            ex.open_request("DEMO-LV-001")
            details = ex.get_request_details()
            ex.approve_request("approved by automation")
            status = ex.get_current_status("DEMO-LV-001")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        headless: Optional[bool] = None,
        timeout_ms: Optional[int] = None,
    ) -> None:
        # Resolved here, not in the signature, so the environment is read now.
        self.base_url = (base_url or default_base_url()).rstrip("/")
        self.headless = default_headless() if headless is None else headless
        self.timeout_ms = timeout_ms if timeout_ms is not None else default_timeout_ms()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._current_record_id: Optional[str] = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> "LeaveApprovalExecutor":
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()
        self._page.set_default_timeout(self.timeout_ms)
        return self

    def stop(self) -> None:
        for closer in (self._browser, self._playwright):
            if closer is None:
                continue
            try:
                closer.close() if closer is self._browser else closer.stop()
            except Exception:  # noqa: BLE001 - teardown must never mask a real error
                logger.debug("Ignoring error while closing the browser", exc_info=True)
        self._page = None
        self._browser = None
        self._playwright = None

    def __enter__(self) -> "LeaveApprovalExecutor":
        return self.start()

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise ExecutionError("Executor is not started; use it as a context manager.")
        return self._page

    # -- navigation --------------------------------------------------------

    def open_queue(self) -> None:
        """Navigate to the leave-application list screen."""
        self.page.goto(
            f"{self.base_url}/leave-applications", wait_until="domcontentloaded"
        )
        self._require("leave-list", "the leave application list did not load")

    def open_request(self, record_id: str) -> None:
        """Open one request's detail panel, by clicking its row link on the queue.

        Navigating by clicking rather than by constructing a detail URL is
        deliberate: it exercises the same path a human takes, so a broken list
        screen is caught here rather than silently bypassed.
        """
        self.open_queue()
        try:
            self.page.click(f'[data-testid="open-{record_id}"]')
            self.page.wait_for_selector('[data-testid="detail-panel"]')
        except PlaywrightTimeoutError as exc:
            raise ExecutionError(
                f"Could not open record {record_id}: no row for it on the queue screen, "
                "or its detail panel did not render."
            ) from exc

        shown = self._text("detail-record-id")
        if shown != record_id:
            raise ExecutionError(
                f"Opened the wrong record: expected {record_id}, the detail panel shows {shown}."
            )
        self._current_record_id = record_id

    # -- reading -----------------------------------------------------------

    def get_request_details(self) -> dict[str, str]:
        """Read the fields off the currently open detail panel.

        Returns raw on-screen strings. No parsing, no normalisation, no
        interpretation - whatever the screen says is what the caller gets.
        """
        self._require("detail-panel", "no detail panel is open")
        return {
            "record_id": self._text("detail-record-id"),
            "employee_id": self._text("detail-employee-id"),
            "employee_name": self._text("detail-employee-name"),
            "request_type": self._text("detail-request-type"),
            "request_date": self._text("detail-request-date"),
            "department": self._text("detail-department"),
            "status": self._text("detail-status"),
            "prior_approval_note": self._text("detail-prior-approval"),
        }

    def get_current_status(self, record_id: str) -> str:
        """Re-read a record's status FROM THE QUEUE SCREEN.

        Reading from the list rather than from the detail page that submitted the
        action is what makes verification independent. A detail page rendered
        straight after a POST could show an optimistic value; the queue is a
        fresh render of the store from a different route.
        """
        self.open_queue()
        try:
            return self._text(f"row-status-{record_id}")
        except ExecutionError as exc:
            raise ExecutionError(
                f"Record {record_id} is not present on the queue screen, so its status "
                "could not be re-read."
            ) from exc

    # -- acting ------------------------------------------------------------

    def approve_request(self, comment: Optional[str] = None) -> None:
        """Click 承認 on the open detail panel, optionally leaving a comment."""
        self._submit("approve-button", comment, "承認")

    def reject_request(self, comment: Optional[str] = None) -> None:
        """Click 差戻し on the open detail panel, optionally leaving a comment.

        Reachable only through the human-review path. The policy layer never
        routes here automatically - `allow_auto_rejection` is false because the
        reject control was never observed being used in Dataset B.
        """
        self._submit("reject-button", comment, "差戻し")

    def _submit(self, button_testid: str, comment: Optional[str], label: str) -> None:
        self._require("detail-panel", "no detail panel is open")

        button = self.page.locator(f'[data-testid="{button_testid}"]')
        if button.count() == 0:
            raise ExecutionError(f"The {label} control is not present on this screen.")
        if button.is_disabled():
            raise ExecutionError(
                f"The {label} control is disabled; this record is not actionable "
                "(it has most likely already been processed)."
            )

        if comment:
            self.page.fill('[data-testid="comment-input"]', comment)

        try:
            button.click()
            # The form is POST-redirect-GET, so a successful submit lands back on
            # a rendered detail page rather than leaving us on a posted form.
            self.page.wait_for_selector('[data-testid="detail-panel"]')
        except PlaywrightTimeoutError as exc:
            raise ExecutionError(
                f"Clicking {label} did not produce a rendered result page."
            ) from exc

        error = self.page.locator('[data-testid="action-error"]')
        if error.count() > 0:
            raise ExecutionError(
                f"The HR system refused the action: {error.inner_text().strip()}"
            )

    # -- helpers -----------------------------------------------------------

    def _require(self, testid: str, message: str) -> None:
        if self.page.locator(f'[data-testid="{testid}"]').count() == 0:
            raise ExecutionError(f"{message} (expected [data-testid='{testid}']).")

    def _text(self, testid: str) -> str:
        locator = self.page.locator(f'[data-testid="{testid}"]')
        if locator.count() == 0:
            raise ExecutionError(f"No element with [data-testid='{testid}'] on this page.")
        return locator.first.inner_text().strip()
