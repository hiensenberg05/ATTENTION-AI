"""The mock internal HR application: a real browser target for the executor.

Separate from the React operations console. It is a plain server-rendered web app
with its own mutable store, so that "approve this request" means navigating and
clicking in a system the platform does not own, and "verify it worked" means
independently re-reading that system afterwards.
"""

from .router import BASE_PATH, router
from .store import store

__all__ = ["router", "store", "BASE_PATH"]
