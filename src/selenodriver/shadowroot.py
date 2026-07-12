from __future__ import annotations

import uuid
from typing import Any

from .by import By, locator_to_css
from .element import WebElement
from .exceptions import NoSuchElementException


class ShadowRoot:
    def __init__(self, raw: Any, runner: Any, driver: Any = None):
        self._raw = raw
        self._runner = runner
        self._driver = driver

    def find_element(self, by: str = By.CSS_SELECTOR, value: str | None = None) -> WebElement:
        elements = self.find_elements(by, value)
        if not elements:
            raise NoSuchElementException(f"No shadow element found using {by}={value!r}")
        return elements[0]

    def find_elements(self, by: str = By.CSS_SELECTOR, value: str | None = None) -> list[WebElement]:
        if value is None:
            raise ValueError("value is required")
        if by == By.XPATH:
            return self._find_elements_by_xpath(value)
        selector = locator_to_css(by, value)
        query_selector_all = getattr(self._raw, "query_selector_all", None)
        if query_selector_all is not None:
            raw_elements = self._runner.run(query_selector_all(selector)) or []
            return [WebElement(raw, self._runner, self._driver) for raw in raw_elements]
        apply = getattr(self._raw, "apply", None)
        if apply is not None:
            raw_elements = self._runner.run(apply(f"(root) => Array.from(root.querySelectorAll({selector!r}))", return_by_value=True)) or []
            return [WebElement(raw, self._runner, self._driver) for raw in raw_elements]
        return []

    def _find_elements_by_xpath(self, xpath: str) -> list[WebElement]:
        apply = getattr(self._raw, "apply", None)
        query_selector_all = getattr(self._raw, "query_selector_all", None)
        if apply is None or query_selector_all is None:
            raise NotImplementedError("ShadowRoot XPath lookup requires apply() and query_selector_all() support")
        token = uuid.uuid4().hex
        selector = f'[data-selenodriver-shadow-xpath="{token}"]'
        try:
            self._runner.run(apply(
                """
                (root, xpath, token) => {
                  const result = (root.ownerDocument || document).evaluate(
                    xpath, root, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
                  );
                  for (let i = 0; i < result.snapshotLength; i++) {
                    const node = result.snapshotItem(i);
                    const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
                    if (element) element.setAttribute('data-selenodriver-shadow-xpath', token);
                  }
                  return result.snapshotLength;
                }
                """,
                xpath,
                token,
                return_by_value=True,
            ))
            raw_elements = self._runner.run(query_selector_all(selector)) or []
            return [WebElement(raw, self._runner, self._driver) for raw in raw_elements]
        finally:
            self._runner.run(apply(
                "(root, token) => root.querySelectorAll(`[data-selenodriver-shadow-xpath=\"${token}\"]`).forEach(el => el.removeAttribute('data-selenodriver-shadow-xpath'))",
                token,
                return_by_value=True,
            ))

    @property
    def raw(self) -> Any:
        return self._raw
