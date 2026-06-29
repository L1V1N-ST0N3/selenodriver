from __future__ import annotations

from typing import Any


class Alert:
    def __init__(self, driver: Any):
        self._driver = driver

    @property
    def text(self) -> str:
        dialog = self._driver._current_alert
        return getattr(dialog, "message", "") if dialog is not None else ""

    def accept(self) -> None:
        self._handle(True)

    def dismiss(self) -> None:
        self._handle(False)

    def send_keys(self, keys_to_send: str) -> None:
        self._driver._alert_prompt_text = str(keys_to_send)

    def _handle(self, accept: bool) -> None:
        from nodriver import cdp

        prompt_text = self._driver._alert_prompt_text
        command = cdp.page.handle_java_script_dialog(accept=accept, prompt_text=prompt_text)
        self._driver._runner.run(self._driver.raw_tab.send(command))
        self._driver._current_alert = None
        self._driver._alert_prompt_text = None
