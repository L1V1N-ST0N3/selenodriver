from __future__ import annotations

import base64
import random
import uuid
from collections.abc import Callable, Sequence
from typing import Any, Iterable

from .by import By, locator_to_css
from .exceptions import ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException
from .hangul import split_input_runs
from .interactions import ClickResult
from .keys import dispatch_ime_text, dispatch_insert_text, dispatch_key_press, dispatch_text, is_special_key, split_key_sequence


class WebElement:
    def __init__(self, raw: Any, runner: Any, driver: Any = None):
        self._raw = raw
        self._runner = runner
        self._driver = driver

    @property
    def text(self) -> str:
        value = getattr(self._raw, "text", "")
        return self._runner.run(value() if callable(value) else value) or ""

    @property
    def tag_name(self) -> str:
        value = getattr(self._raw, "tag_name", None) or getattr(self._raw, "tag", None)
        value = self._runner.run(value() if callable(value) else value)
        if value:
            return str(value).lower()
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return ""
        return str(self._runner.run(apply("(el) => el.tagName.toLowerCase()", return_by_value=True)) or "")

    def click(self, *, input_type: str = "mouse", use_touch: bool = False) -> ClickResult | None:
        if (
            self._driver is not None
            and self._driver._randomize_clicks
            and input_type == "mouse"
            and not use_touch
        ):
            return self.random_click(
                input_type=self._driver._default_click_input,
                fallback=self._driver._click_fallback,
            )
        if use_touch:
            input_type = "touch"
        if input_type == "js":
            self.js_click()
            return None
        if input_type == "touch":
            self.touch_click()
            return None
        if input_type != "mouse":
            raise ValueError("input_type must be 'mouse', 'touch', or 'js'")
        self.mouse_click()
        return None

    def mouse_click(self) -> None:
        if self._driver is not None:
            self._wait_until_ready_for_action()
            self.scroll_into_view()
            self._mouse_click_center()
            return
        self._runner.run(self._raw.click())

    def touch_click(self) -> None:
        if self._driver is None:
            self._runner.run(self._raw.click())
            return
        self._wait_until_ready_for_action()
        self.touch_scroll_into_view()
        self._touch_click_center()

    def random_click(
        self,
        *,
        input_type: str = "touch",
        fallback: bool | Sequence[str] = True,
        margin: float = 0.125,
        verify: Callable[[ClickResult], bool] | None = None,
        rng: random.Random | None = None,
    ) -> ClickResult:
        """Click a random safe point and optionally try conservative fallbacks."""
        if self._driver is None:
            raise ElementNotInteractableException("random_click requires an attached driver")
        if input_type not in {"touch", "mouse"}:
            raise ValueError("input_type must be 'touch' or 'mouse'")
        self._wait_until_ready_for_action()
        if input_type == "touch":
            self.touch_scroll_into_view()
        else:
            self.scroll_into_view()

        rect = self._viewport_rect()
        width = float(rect["width"])
        height = float(rect["height"])
        if width <= 0 or height <= 0:
            raise ElementNotInteractableException("Element has no clickable area")
        margin_x = self._click_margin(width, margin)
        margin_y = self._click_margin(height, margin)
        generator = rng or random
        random_x = float(rect["x"]) + generator.uniform(margin_x, max(margin_x, width - margin_x))
        random_y = float(rect["y"]) + generator.uniform(margin_y, max(margin_y, height - margin_y))
        center_x = float(rect["x"]) + width / 2
        center_y = float(rect["y"]) + height / 2

        stages: list[tuple[str, float | None, float | None]] = [
            (f"{input_type}:random", random_x, random_y)
        ]
        if fallback is True:
            stages.extend(
                [(f"{input_type}:center", center_x, center_y)]
            )
            other = "mouse" if input_type == "touch" else "touch"
            stages.extend([(f"{other}:center", center_x, center_y), ("js", None, None)])
        elif fallback:
            fallback_methods = [fallback] if isinstance(fallback, str) else fallback
            for method in fallback_methods:
                if method not in {"touch", "mouse", "js"}:
                    raise ValueError("fallback entries must be 'touch', 'mouse', or 'js'")
                stages.append(
                    ("js", None, None)
                    if method == "js"
                    else (f"{method}:center", center_x, center_y)
                )

        attempts: list[str] = []
        last_error: Exception | None = None
        url_before = self._driver.current_url
        for method, x, y in stages:
            attempts.append(method)
            try:
                if method == "js":
                    self.js_click()
                else:
                    if not self._point_receives_click(float(x), float(y)):
                        raise ElementClickInterceptedException(
                            f"Another element covers click point ({x:.1f}, {y:.1f})"
                        )
                    selected = method.split(":", 1)[0]
                    self._driver._dispatch_point_click(float(x), float(y), input_type=selected)
                result = ClickResult(
                    method=method,
                    x=x,
                    y=y,
                    attempts=tuple(attempts),
                    url_before=url_before,
                    url_after=self._driver.current_url,
                    verified=True,
                )
                if verify is not None and not bool(verify(result)):
                    last_error = ElementClickInterceptedException(
                        f"Click verification failed after {method}"
                    )
                    continue
                self._driver._record_click(result)
                return result
            except (ElementNotInteractableException, NoSuchElementException):
                raise
            except Exception as error:
                last_error = error
        if last_error is not None:
            raise last_error
        raise ElementClickInterceptedException("No click strategy succeeded")

    @staticmethod
    def _click_margin(size: float, margin: float) -> float:
        requested = size * margin if 0 <= margin < 1 else margin
        return min(max(0.5, float(requested)), max(0.5, size / 2))

    def _point_receives_click(self, x: float, y: float) -> bool:
        if self._driver is None:
            return True
        return bool(
            self._driver.execute_script(
                """
                const el = arguments[0];
                const hit = document.elementFromPoint(arguments[1], arguments[2]);
                return Boolean(hit && (hit === el || el.contains(hit) || hit.contains(el)));
                """,
                self,
                x,
                y,
            )
        )

    def js_click(self) -> None:
        apply = getattr(self._raw, "apply", None)
        if apply is not None:
            self._runner.run(apply("(el) => el.click()", return_by_value=True))
            return
        self._runner.run(self._raw.click())

    def send_cdp(self, command: Any) -> Any:
        if self._driver is not None:
            return self._driver.send_cdp(command)
        tab = getattr(self._raw, "tab", None) or getattr(self._raw, "_tab", None)
        if tab is None:
            raise RuntimeError("Element has no driver or tab for CDP command dispatch")
        return self._runner.run(tab.send(command))

    def send_keys(
        self,
        *value: object,
        delay: float = 0.0,
        mode: str = "auto",
        focus: bool | None = None,
    ) -> None:
        if mode not in {"auto", "key", "text", "ime", "jamo"}:
            raise ValueError("mode must be 'auto', 'key', 'text', 'ime', or 'jamo'")
        if mode == "jamo":
            mode = "ime"
        if self._driver is not None:
            text_length = sum(len(str(item)) for item in value)
            self._driver._record_input(
                mode=mode, text_length=text_length, source="WebElement.send_keys"
            )
        self._wait_until_ready_for_action()
        if focus is None:
            focus = mode == "ime"
        if focus:
            self.mouse_click()
        focus_method = getattr(self._raw, "focus", None)
        if focus_method is not None and callable(focus_method):
            self._runner.run(focus_method())
        for chunk in split_key_sequence(*value):
            if is_special_key(chunk) and self._driver is not None:
                dispatch_key_press(self._driver.raw_tab, self._runner, chunk)
            elif self._driver is not None:
                self._send_text_chunk(chunk, delay=delay, mode=mode)
            else:
                self._runner.run(self._raw.send_keys(chunk))

    def _send_text_chunk(self, chunk: str, *, delay: float, mode: str) -> None:
        if mode == "key":
            for kind, part in split_input_runs(chunk):
                if kind == "text":
                    dispatch_insert_text(self._driver.raw_tab, self._runner, part, delay=delay)
                else:
                    dispatch_text(self._driver.raw_tab, self._runner, part, delay=delay)
            return
        if mode == "ime":
            self._send_jamo_chunk(chunk, delay=delay)
            return
        if mode == "text":
            dispatch_insert_text(self._driver.raw_tab, self._runner, chunk, delay=delay)
            return
        for kind, part in split_input_runs(chunk):
            if kind == "hangul":
                dispatch_insert_text(self._driver.raw_tab, self._runner, part, delay=delay)
            elif kind == "key":
                dispatch_text(self._driver.raw_tab, self._runner, part, delay=delay)
            else:
                dispatch_insert_text(self._driver.raw_tab, self._runner, part, delay=delay)

    def _send_jamo_chunk(self, chunk: str, *, delay: float) -> None:
        for kind, part in split_input_runs(chunk):
            if kind == "hangul":
                dispatch_ime_text(self._driver.raw_tab, self._runner, part, delay=delay)
            elif kind == "key":
                dispatch_text(self._driver.raw_tab, self._runner, part, delay=delay)
            else:
                dispatch_insert_text(self._driver.raw_tab, self._runner, part, delay=delay)

    def send_keys_js(self, *value: object) -> None:
        """Append text through JavaScript; use send_keys() for real keyboard input."""
        self._wait_until_ready_for_action()
        chunks = list(split_key_sequence(*value))
        text = "".join(chunk for chunk in chunks if not is_special_key(chunk))
        if self._driver is not None:
            self._driver.execute_script(
                """
                const el = arguments[0];
                const text = String(arguments[1]);
                if (el.isContentEditable) {
                    el.textContent += text;
                } else {
                    const setter = Object.getOwnPropertyDescriptor(
                        Object.getPrototypeOf(el), 'value'
                    )?.set;
                    if (setter) setter.call(el, String(el.value || '') + text);
                    else el.value = String(el.value || '') + text;
                }
                el.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: text}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
                """,
                self,
                text,
            )
            return
        self._runner.run(self._raw.send_keys(text))

    def clear(self) -> None:
        clear_input = getattr(self._raw, "clear_input", None)
        if clear_input is not None:
            self._runner.run(clear_input())
            return
        self._runner.run(self._raw.apply("(el) => { el.value = ''; el.dispatchEvent(new Event('input')); }"))

    def submit(self) -> None:
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return
        script = """
        (el) => {
          const form = el.form || el.closest('form');
          if (!form) throw new Error('Element is not inside a form');
          if (form.requestSubmit) form.requestSubmit();
          else form.submit();
        }
        """
        self._runner.run(apply(script, return_by_value=True))

    def scroll_into_view(self, align_to_top: bool = True) -> None:
        scroll_into_view = getattr(self._raw, "scroll_into_view", None)
        if scroll_into_view is not None:
            self._runner.run(scroll_into_view())
            return
        apply = getattr(self._raw, "apply", None)
        if apply is not None:
            self._runner.run(apply(f"(el) => el.scrollIntoView({str(bool(align_to_top)).lower()})", return_by_value=True))

    def touch_scroll_into_view(self, *, max_swipes: int = 10, steps: int = 8) -> None:
        if self._driver is None:
            self.scroll_into_view()
            return
        for _ in range(max_swipes):
            rect = self._viewport_rect()
            viewport = self._driver._viewport_size()
            if 0 <= rect["y"] and rect["y"] + rect["height"] <= viewport["height"]:
                return
            center_y = rect["y"] + rect["height"] / 2
            target_y = viewport["height"] / 2
            self._driver.touch_scroll_by(0, int(center_y - target_y), steps=steps)

    def get_attribute(self, name: str) -> Any:
        attrs = getattr(self._raw, "attrs", None) or getattr(self._raw, "attributes", None)
        attrs = self._runner.run(attrs() if callable(attrs) else attrs)
        if isinstance(attrs, dict):
            if name in attrs:
                return attrs[name]
        if isinstance(attrs, Iterable) and not isinstance(attrs, (str, bytes)):
            items = list(attrs)
            for index in range(0, len(items) - 1, 2):
                if items[index] == name:
                    return items[index + 1]

        # Selenium's get_attribute() also exposes DOM properties such as
        # outerHTML and innerText, which are not present in the attribute map.
        apply = getattr(self._raw, "apply", None)
        if apply is not None:
            script = f"""
            (el) => {{
              const value = el[{name!r}];
              if (value === undefined || value === null || typeof value === 'object') {{
                return el.getAttribute({name!r});
              }}
              return value;
            }}
            """
            value = self._runner.run(apply(script, return_by_value=True))
            if value is not None:
                return value
        get_js_attributes = getattr(self._raw, "get_js_attributes", None)
        if get_js_attributes is not None:
            js_attrs = self._runner.run(get_js_attributes())
            if isinstance(js_attrs, dict):
                return js_attrs.get(name)
        return None

    def get_dom_attribute(self, name: str) -> Any:
        attrs = getattr(self._raw, "attrs", None) or getattr(self._raw, "attributes", None)
        attrs = self._runner.run(attrs() if callable(attrs) else attrs)
        if isinstance(attrs, dict):
            return attrs.get(name)
        if isinstance(attrs, Iterable) and not isinstance(attrs, (str, bytes)):
            items = list(attrs)
            for index in range(0, len(items) - 1, 2):
                if items[index] == name:
                    return items[index + 1]
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return None
        return self._runner.run(
            apply(f"(el) => el.getAttribute({name!r})", return_by_value=True)
        )

    def get_property(self, name: str) -> Any:
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return None
        return self._runner.run(apply(f"(el) => el[{name!r}]", return_by_value=True))

    def value_of_css_property(self, property_name: str) -> str:
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return ""
        script = f"(el) => window.getComputedStyle(el).getPropertyValue({property_name!r})"
        return self._runner.run(apply(script, return_by_value=True)) or ""

    def screenshot(self, filename: str) -> bool:
        data = self.screenshot_as_png
        with open(filename, "wb") as file:
            file.write(data)
        return True

    @property
    def screenshot_as_base64(self) -> str:
        if self._driver is None:
            return ""
        script = """
        async (el) => {
          const rect = el.getBoundingClientRect();
          const canvas = document.createElement('canvas');
          canvas.width = Math.max(1, Math.ceil(rect.width));
          canvas.height = Math.max(1, Math.ceil(rect.height));
          const ctx = canvas.getContext('2d');
          const data = await new XMLSerializer().serializeToString(el);
          const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}">
            <foreignObject width="100%" height="100%">${data}</foreignObject>
          </svg>`;
          const img = new Image();
          const url = URL.createObjectURL(new Blob([svg], {type: 'image/svg+xml'}));
          await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
            img.src = url;
          });
          ctx.drawImage(img, 0, 0);
          URL.revokeObjectURL(url);
          return canvas.toDataURL('image/png').split(',')[1];
        }
        """
        return self._runner.run(self._raw.apply(script, return_by_value=True)) or ""

    @property
    def screenshot_as_png(self) -> bytes:
        value = self.screenshot_as_base64
        return base64.b64decode(value) if value else b""

    @property
    def size(self) -> dict[str, float]:
        rect = self.rect
        return {"height": rect["height"], "width": rect["width"]}

    @property
    def location(self) -> dict[str, float]:
        rect = self.rect
        return {"x": rect["x"], "y": rect["y"]}

    @property
    def location_once_scrolled_into_view(self) -> dict[str, float]:
        self.scroll_into_view()
        rect = self._viewport_rect()
        return {"x": rect["x"], "y": rect["y"]}

    @property
    def id(self) -> str:
        value = getattr(self._raw, "backend_node_id", None)
        if value is None:
            value = getattr(self._raw, "node_id", None)
        return str(value if value is not None else id(self._raw))

    @property
    def parent(self) -> Any:
        return self._driver

    @property
    def session_id(self) -> str | None:
        return self._driver.session_id if self._driver is not None else None

    @property
    def accessible_name(self) -> str:
        if self._driver is None:
            return str(self.get_attribute("aria-label") or self.get_attribute("alt") or "")
        return str(
            self._driver.execute_script(
                """
                const el = arguments[0];
                const labelledBy = el.getAttribute('aria-labelledby');
                if (labelledBy) {
                  const text = labelledBy.split(/\\s+/).map((id) => document.getElementById(id)?.innerText || '').join(' ').trim();
                  if (text) return text;
                }
                return el.getAttribute('aria-label') || el.getAttribute('alt') ||
                       el.getAttribute('title') || (el.innerText || '').trim();
                """,
                self,
            ) or ""
        )

    @property
    def aria_role(self) -> str:
        role = self.get_dom_attribute("role")
        return str(role or self.tag_name or "")

    @property
    def rect(self) -> dict[str, float]:
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return {"height": 0, "width": 0, "x": 0, "y": 0}
        script = """
        (el) => {
          const rect = el.getBoundingClientRect();
          return {
            height: rect.height,
            width: rect.width,
            x: rect.x + window.scrollX,
            y: rect.y + window.scrollY
          };
        }
        """
        rect = self._runner.run(apply(script, return_by_value=True)) or {}
        return {
            "height": rect.get("height", 0),
            "width": rect.get("width", 0),
            "x": rect.get("x", 0),
            "y": rect.get("y", 0),
        }

    def _mouse_click_center(self) -> None:
        from nodriver import cdp

        rect = self._viewport_rect()
        x = rect["x"] + rect["width"] / 2
        y = rect["y"] + rect["height"] / 2
        pressed = cdp.input_.dispatch_mouse_event(
            "mousePressed",
            x=x,
            y=y,
            button=cdp.input_.MouseButton("left"),
            buttons=1,
            click_count=1,
        )
        released = cdp.input_.dispatch_mouse_event(
            "mouseReleased",
            x=x,
            y=y,
            button=cdp.input_.MouseButton("left"),
            buttons=0,
            click_count=1,
        )
        self._runner.run(self._driver.raw_tab.send(pressed))
        self._runner.run(self._driver.raw_tab.send(released))

    def _touch_click_center(self) -> None:
        from nodriver import cdp

        rect = self._viewport_rect()
        x = rect["x"] + rect["width"] / 2
        y = rect["y"] + rect["height"] / 2
        point = cdp.input_.TouchPoint(x=x, y=y, radius_x=1, radius_y=1, force=1, id_=1)
        touch_start = cdp.input_.dispatch_touch_event("touchStart", [point])
        touch_end = cdp.input_.dispatch_touch_event("touchEnd", [])
        self._runner.run(self._driver.raw_tab.send(touch_start))
        self._runner.run(self._driver.raw_tab.send(touch_end))

    def _viewport_rect(self) -> dict[str, float]:
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return {"height": 0, "width": 0, "x": 0, "y": 0}
        script = """
        (el) => {
          const rect = el.getBoundingClientRect();
          return {
            height: rect.height,
            width: rect.width,
            x: rect.x,
            y: rect.y
          };
        }
        """
        rect = self._runner.run(apply(script, return_by_value=True)) or {}
        return {
            "height": rect.get("height", 0),
            "width": rect.get("width", 0),
            "x": rect.get("x", 0),
            "y": rect.get("y", 0),
        }

    def is_displayed(self) -> bool:
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return True
        script = """
        (el) => {
          const style = window.getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          return style && style.visibility !== 'hidden' &&
                 style.display !== 'none' &&
                 rect.width > 0 && rect.height > 0;
        }
        """
        return bool(self._runner.run(apply(script, return_by_value=True)))

    def is_enabled(self) -> bool:
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return True
        script = """
        (el) => {
          return !el.disabled && el.getAttribute('aria-disabled') !== 'true';
        }
        """
        return bool(self._runner.run(apply(script, return_by_value=True)))

    def is_selected(self) -> bool:
        apply = getattr(self._raw, "apply", None)
        if apply is None:
            return False
        script = """
        (el) => {
          return Boolean(el.checked || el.selected);
        }
        """
        return bool(self._runner.run(apply(script, return_by_value=True)))

    def _wait_until_ready_for_action(self) -> None:
        if self._driver is None or not self._driver._auto_wait:
            return
        deadline = self._monotonic() + self._driver._auto_wait_timeout
        while True:
            if self.is_displayed() and self.is_enabled():
                return
            if self._monotonic() >= deadline:
                raise ElementNotInteractableException(
                    f"Element was not actionable after {self._driver._auto_wait_timeout} seconds"
                )
            self._sleep(0.05)

    def _monotonic(self) -> float:
        import time

        return time.monotonic()

    def _sleep(self, seconds: float) -> None:
        import time

        time.sleep(seconds)

    def find_element(self, by: str = By.CSS_SELECTOR, value: str | None = None) -> "WebElement":
        elements = self.find_elements(by, value)
        if not elements:
            raise NoSuchElementException(f"No element found using {by}={value!r}")
        return elements[0]

    def find_elements(self, by: str = By.CSS_SELECTOR, value: str | None = None) -> list["WebElement"]:
        if value is None:
            raise ValueError("value is required")
        if by == By.XPATH:
            return self._find_elements_by_xpath(value)
        selector = locator_to_css(by, value)
        raw_elements = self._runner.run(self._raw.query_selector_all(selector)) or []
        return [WebElement(raw, self._runner, self._driver) for raw in raw_elements]

    def _find_elements_by_xpath(self, xpath: str) -> list["WebElement"]:
        parent_steps = self._relative_parent_steps(xpath)
        is_nodriver_element = type(self._raw).__module__.startswith("nodriver.")
        if parent_steps is not None and is_nodriver_element:
            current = self._raw
            try:
                for _ in range(parent_steps):
                    current = current.parent
                    if current is None:
                        return []
            except RuntimeError:
                update = getattr(current, "update", None)
                if update is None:
                    return []
                self._runner.run(update())
                current = self._raw
                for _ in range(parent_steps):
                    current = current.parent
                    if current is None:
                        return []
            return [WebElement(current, self._runner, self._driver)]

        apply = getattr(self._raw, "apply", None)
        query_selector_all = getattr(self._raw, "query_selector_all", None)
        if apply is None or query_selector_all is None:
            raise NotImplementedError("Nested XPath lookup requires element apply() and query_selector_all() support")

        marker_name = "data-selenodriver-xpath"
        marker_value = uuid.uuid4().hex
        selector = f'[{marker_name}="{marker_value}"]'
        script = f"""
        (el) => {{
          const result = document.evaluate(
            {xpath!r},
            el,
            null,
            XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
            null
          );
          const marked = [];
          for (let i = 0; i < result.snapshotLength; i += 1) {{
            let node = result.snapshotItem(i);
            if (node && node.nodeType !== Node.ELEMENT_NODE) {{
              node = node.parentElement;
            }}
            if (node && node.setAttribute) {{
              node.setAttribute({marker_name!r}, {marker_value!r});
              marked.push(node);
            }}
          }}
          return marked.length;
        }}
        """
        cleanup_script = f"""
        (el) => {{
          const doc = el.ownerDocument || document;
          doc.querySelectorAll({selector!r}).forEach((node) => {{
            node.removeAttribute({marker_name!r});
          }});
        }}
        """
        self._runner.run(apply(script, return_by_value=True))
        try:
            includes_self = bool(
                self._runner.run(
                    apply(
                        f"(el) => el.getAttribute({marker_name!r}) === {marker_value!r}",
                        return_by_value=True,
                    )
                )
            )
            use_document_query = self._driver is not None and is_nodriver_element
            if use_document_query:
                raw_elements = self._runner.run(
                    self._driver.raw_tab.query_selector_all(selector)
                ) or []
            else:
                raw_elements = self._runner.run(query_selector_all(selector)) or []
        finally:
            self._runner.run(apply(cleanup_script, return_by_value=True))
        if includes_self and not use_document_query:
            raw_elements = [self._raw, *raw_elements]
        return [WebElement(raw, self._runner, self._driver) for raw in raw_elements]

    @staticmethod
    def _relative_parent_steps(xpath: str) -> int | None:
        parts = xpath.strip().split("/")
        if not parts or parts[0] != "." or any(part != ".." for part in parts[1:]):
            return None
        return len(parts) - 1

    @property
    def shadow_root(self):
        from .shadowroot import ShadowRoot

        raw_shadow = getattr(self._raw, "shadow_root", None)
        if raw_shadow is None:
            shadow_roots = getattr(self._raw, "shadow_roots", None)
            if shadow_roots:
                raw_shadow = shadow_roots[0]
        if raw_shadow is None:
            raise NoSuchElementException("Element has no shadow root")
        return ShadowRoot(raw_shadow, self._runner, self._driver)

    @property
    def raw(self) -> Any:
        return self._raw
