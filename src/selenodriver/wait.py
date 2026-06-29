from __future__ import annotations

import time
from typing import Any, Callable

from .exceptions import NoSuchElementException, TimeoutException


class WebDriverWait:
    def __init__(self, driver: Any, timeout: float, poll_frequency: float = 0.5, ignored_exceptions: tuple[type[Exception], ...] | None = None):
        self._driver = driver
        self._timeout = timeout
        self._poll = poll_frequency
        exceptions = [NoSuchElementException]
        if ignored_exceptions:
            exceptions.extend(ignored_exceptions)
        self._ignored_exceptions = tuple(exceptions)

    def until(self, method: Callable[[Any], Any], message: str = "") -> Any:
        end_time = time.monotonic() + self._timeout
        last_exc: Exception | None = None
        while True:
            try:
                value = method(self._driver)
                if value:
                    return value
            except self._ignored_exceptions as exc:
                last_exc = exc
            if time.monotonic() > end_time:
                detail = message or f"Timed out after {self._timeout} seconds"
                if last_exc is not None:
                    detail = f"{detail}: {last_exc}"
                raise TimeoutException(detail)
            time.sleep(self._poll)

    def until_not(self, method: Callable[[Any], Any], message: str = "") -> bool:
        end_time = time.monotonic() + self._timeout
        while True:
            value = method(self._driver)
            if not value:
                return True
            if time.monotonic() > end_time:
                raise TimeoutException(message or f"Timed out after {self._timeout} seconds")
            time.sleep(self._poll)
