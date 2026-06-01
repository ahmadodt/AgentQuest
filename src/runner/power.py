from __future__ import annotations

import ctypes
import os
from contextlib import contextmanager
from typing import Iterator


ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _set_thread_execution_state(flags: int) -> int:
    kernel32 = getattr(ctypes, "windll", None)
    if kernel32 is None:
        return 0
    return int(kernel32.kernel32.SetThreadExecutionState(flags) or 0)


@contextmanager
def prevent_system_sleep() -> Iterator[None]:
    if os.name != "nt":
        yield
        return

    previous_state = _set_thread_execution_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    try:
        yield
    finally:
        if previous_state:
            _set_thread_execution_state(ES_CONTINUOUS)
