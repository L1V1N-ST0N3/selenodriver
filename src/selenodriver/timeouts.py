from __future__ import annotations

from typing import Any


class Timeouts:
    def __init__(self, driver: Any):
        self._driver = driver

    @property
    def implicit_wait(self) -> float:
        return self._driver._implicit_wait

    @property
    def page_load(self) -> float:
        return self._driver._page_load_timeout

    @property
    def script(self) -> float:
        return self._driver._script_timeout
