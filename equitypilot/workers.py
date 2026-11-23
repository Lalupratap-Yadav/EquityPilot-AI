"""One long-lived background worker process for heavy, self-contained jobs: bulk quote downloads (yfinance spends
~0.1 s of CPU per symbol) and the universe-metrics recompute (several seconds of pandas work after a restart).

Python runs one thread at a time per process, so CPU-heavy work in a background thread slows every web request in the
same process. Running these jobs in a separate process keeps request handling fast.

The worker is used only after the web server enables it at start-up (`enable()`); scripts, the command line, the
Streamlit workbench and the tests that import these modules never start a process. Set EQUITYPILOT_WORKER_PROCESS=0 to
turn it off. If the worker cannot start or fails, callers run the job in-process instead (`WorkerUnavailable`).
"""
from __future__ import annotations

import logging
import os
import threading

log = logging.getLogger(__name__)

_STATE: dict = {"ex": None, "enabled": False, "broken": False}
_LOCK = threading.Lock()


class WorkerUnavailable(RuntimeError):
    """The worker process is disabled, broken or failed this job; run the job in-process."""


def enable() -> None:
    _STATE["enabled"] = os.environ.get("EQUITYPILOT_WORKER_PROCESS", "1") != "0"


def available() -> bool:
    return bool(_STATE["enabled"]) and not _STATE["broken"]


def _exit_with_parent() -> None:
    """Runs inside the worker when it starts: end the worker as soon as the server process that started it is gone.
    (A force-killed server would otherwise leave the worker running for ever, because the worker holds its own end of
    the job queue and so never sees it close.)"""
    import multiprocessing as mp
    parent = mp.parent_process()
    if parent is None:
        return

    def watch():
        parent.join()            # returns when the parent process has exited, however it ended
        os._exit(0)
    threading.Thread(target=watch, name="parent-watch", daemon=True).start()


def _executor():
    with _LOCK:
        if _STATE["ex"] is None:
            import multiprocessing as mp
            from concurrent.futures import ProcessPoolExecutor
            _STATE["ex"] = ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context("spawn"), initializer=_exit_with_parent)
        return _STATE["ex"]


def run(fn, *args, timeout: float = 600):
    """Run fn(*args) in the worker process and return its result. `fn` must be a module-level function and its
    arguments and result must be picklable. Raises WorkerUnavailable when the job could not run there."""
    from concurrent.futures import TimeoutError as FutureTimeout
    from concurrent.futures.process import BrokenProcessPool
    if not available():
        raise WorkerUnavailable("worker process disabled")
    try:
        fut = _executor().submit(fn, *args)
        return fut.result(timeout=timeout)
    except (BrokenProcessPool, FutureTimeout, OSError, RuntimeError) as exc:
        # The process could not start, crashed or is stuck. Every later job would wait for it: stop using it and let
        # callers work in-process. (An ordinary exception raised by the job itself propagates unchanged.)
        log.warning("worker process failed (%s: %s); running jobs in-process from now on", type(exc).__name__, exc)
        _STATE["broken"] = True
        shutdown()
        raise WorkerUnavailable(str(exc)) from exc


def shutdown() -> None:
    with _LOCK:
        if _STATE["ex"] is not None:
            _STATE["ex"].shutdown(wait=False, cancel_futures=True)
            _STATE["ex"] = None
