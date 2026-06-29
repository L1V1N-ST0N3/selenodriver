from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class By:
    ID: str = "id"
    XPATH: str = "xpath"
    LINK_TEXT: str = "link text"
    PARTIAL_LINK_TEXT: str = "partial link text"
    NAME: str = "name"
    TAG_NAME: str = "tag name"
    CLASS_NAME: str = "class name"
    CSS_SELECTOR: str = "css selector"


def locator_to_css(by: str, value: str) -> str:
    if by == By.CSS_SELECTOR:
        return value
    if by == By.ID:
        return f"#{_css_escape(value)}"
    if by == By.NAME:
        return f'[name="{_css_string(value)}"]'
    if by == By.TAG_NAME:
        return value
    if by == By.CLASS_NAME:
        return "." + ".".join(_css_escape(part) for part in value.split())
    raise ValueError(f"Cannot convert locator {by!r} to a CSS selector")


def _css_escape(value: str) -> str:
    escaped = []
    for char in value:
        if char.isalnum() or char in ("-", "_"):
            escaped.append(char)
        else:
            escaped.append("\\" + char)
    return "".join(escaped)


def _css_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
