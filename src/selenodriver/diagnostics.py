from __future__ import annotations

import dataclasses
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DiagnosticSnapshot:
    timestamp: str
    url: str
    current_window_handle: str
    window_handles: tuple[str, ...]
    active_element: dict[str, Any] | None
    element: dict[str, Any] | None
    last_click: dict[str, Any] | None
    last_input: dict[str, Any] | None
    extension_errors: dict[str, tuple[str, ...]]
    error: str | None
    screenshot_path: str | None
    html_path: str | None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class DriverDiagnostics:
    def __init__(self, driver: Any):
        self._driver = driver

    def capture(
        self,
        *,
        element: Any = None,
        error: BaseException | str | None = None,
        screenshot_path: str | Path | None = None,
        html_path: str | Path | None = None,
    ) -> DiagnosticSnapshot:
        screenshot = self._save_screenshot(screenshot_path)
        html = self._save_redacted_html(html_path)
        active = None
        try:
            active = self._describe_element(self._driver.active_element)
        except Exception:
            pass
        extension_errors: dict[str, tuple[str, ...]] = {}
        for extension in self._driver._extensions:
            values = getattr(extension, "last_errors", None)
            if values:
                extension_errors[type(extension).__name__] = tuple(map(str, values))
        click = getattr(self._driver, "_last_click", None)
        return DiagnosticSnapshot(
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat(),
            url=self._safe(lambda: self._driver.current_url, ""),
            current_window_handle=self._safe(
                lambda: self._driver.current_window_handle, ""
            ),
            window_handles=tuple(self._safe(lambda: self._driver.window_handles, [])),
            active_element=active,
            element=self._describe_element(element) if element is not None else None,
            last_click=dataclasses.asdict(click) if dataclasses.is_dataclass(click) else None,
            last_input=dict(self._driver._last_input) if self._driver._last_input else None,
            extension_errors=extension_errors,
            error=str(error) if error is not None else None,
            screenshot_path=screenshot,
            html_path=html,
        )

    def _describe_element(self, element: Any) -> dict[str, Any]:
        return {
            "id": self._safe(lambda: element.get_dom_attribute("id"), None),
            "name": self._safe(lambda: element.get_dom_attribute("name"), None),
            "type": self._safe(lambda: element.get_dom_attribute("type"), None),
            "tag_name": self._safe(lambda: element.tag_name, ""),
            "rect": self._safe(lambda: element.rect, None),
            "displayed": self._safe(lambda: element.is_displayed(), None),
            "enabled": self._safe(lambda: element.is_enabled(), None),
        }

    def _save_screenshot(self, path: str | Path | None) -> str | None:
        if path is None:
            return None
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._driver.save_screenshot(str(target))
        return str(target)

    def _save_redacted_html(self, path: str | Path | None) -> str | None:
        if path is None:
            return None
        html = self._driver.execute_script(
            """
            const root = document.documentElement.cloneNode(true);
            root.querySelectorAll('input').forEach((el) => {
              if (el.hasAttribute('value')) el.setAttribute('value', '[REDACTED]');
              el.removeAttribute('checked');
            });
            root.querySelectorAll('textarea,[contenteditable="true"]').forEach((el) => {
              el.textContent = '[REDACTED]';
            });
            return root.outerHTML;
            """
        )
        if not isinstance(html, str):
            return None
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        return str(target)

    @staticmethod
    def _safe(function, default):
        try:
            return function()
        except Exception:
            return default

