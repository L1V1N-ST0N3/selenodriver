from __future__ import annotations

from typing import Any, Protocol


class SelenoDriverExtension(Protocol):
    def on_attach(self, driver: Any) -> None:
        ...

    def before_navigate(self, driver: Any, url: str) -> None:
        ...

    def after_navigate(self, driver: Any, url: str) -> None:
        ...

    def on_context_changed(self, driver: Any) -> None:
        ...

    def before_quit(self, driver: Any) -> None:
        ...
