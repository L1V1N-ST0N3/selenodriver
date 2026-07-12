from __future__ import annotations

import base64
import re
import time
import uuid
from typing import Any

from .alert import Alert
from .by import By, locator_to_css
from .element import WebElement
from .exceptions import (
    NoAlertPresentException,
    NoSuchElementException,
    NoSuchFrameException,
    NoSuchWindowException,
    SelenoDriverException,
    TimeoutException,
)
from .extensions import SelenoDriverExtension
from .options import Options
from .sync import SyncRunner
from .timeouts import Timeouts


class SwitchTo:
    def __init__(self, driver: "Chrome"):
        self._driver = driver

    def window(self, window_name: str) -> None:
        self._driver.switch_to_window(window_name)

    def frame(self, frame_reference: Any) -> None:
        self._driver.switch_to_frame(frame_reference)

    def default_content(self) -> None:
        self._driver.switch_to_default_content()

    def parent_frame(self) -> None:
        self._driver.switch_to_parent_frame()

    @property
    def active_element(self) -> WebElement:
        return self._driver.active_element

    @property
    def alert(self) -> Alert:
        if self._driver._current_alert is None:
            raise NoAlertPresentException("No alert is currently open")
        return self._driver.alert


class Chrome:
    def __init__(
        self,
        *,
        browser: Any = None,
        tab: Any = None,
        runner: SyncRunner | None = None,
        options: Options | None = None,
        extensions: list[SelenoDriverExtension] | None = None,
        page_load_timeout: float = 30,
        page_load_strategy: str = "normal",
        auto_wait: bool = False,
        auto_wait_timeout: float = 10,
        **kwargs: Any,
    ):
        self._owns_runner = runner is None
        self._runner = runner or SyncRunner()
        self._browser = browser
        self._tab = tab
        self._top_tab = tab
        self._frame_stack: list[Any] = []
        self._page_load_timeout = page_load_timeout
        self._page_load_strategy = page_load_strategy
        self._implicit_wait = 0.0
        self._auto_wait = auto_wait
        self._auto_wait_timeout = float(auto_wait_timeout)
        self._script_timeout = 30.0
        self._current_alert: Any = None
        self._alert_prompt_text: str | None = None
        self._extensions: list[Any] = []
        self._init_script_ids: list[Any] = []
        self._known_window_handles: set[str] = set()
        self.switch_to = SwitchTo(self)
        if self._browser is None:
            import nodriver

            if options is not None:
                kwargs = {**options.to_nodriver_kwargs(), **kwargs}
            self._browser = self._runner.run(nodriver.start(**kwargs))
        if self._tab is None:
            self._tab = getattr(self._browser, "main_tab", None)
            if self._tab is None:
                self._tab = self._runner.run(self._browser.get())
        self._top_tab = self._tab
        self._install_dialog_handler()
        self._known_window_handles = set(self._window_handles_without_update())
        for extension in extensions or []:
            self.use(extension)

    def get(self, url: str) -> None:
        self._notify_extensions("before_navigate", url)
        result = self._runner.run(self._browser.get(url))
        if result is not None:
            self._tab = result
            self._top_tab = result
            self._install_dialog_handler()
        self._wait_for_page_load()
        self._notify_extensions("after_navigate", url)
        self._notify_extensions("on_context_changed")

    def use(self, extension: Any) -> Any:
        self._extensions.append(extension)
        install = getattr(extension, "install", None)
        if callable(install):
            install(self)
        elif callable(extension) and not any(hasattr(extension, name) for name in ("on_attach", "before_navigate", "after_navigate", "on_context_changed", "before_quit")):
            extension(self)
        self._call_extension_hook(extension, "on_attach")
        return extension

    def remove_extension(self, extension: Any) -> None:
        if extension in self._extensions:
            self._extensions.remove(extension)

    def add_init_script(self, source: str, *, run_immediately: bool = True, world_name: str | None = None) -> Any:
        from nodriver import cdp

        script_id = self.send_cdp(
            cdp.page.add_script_to_evaluate_on_new_document(
                source,
                world_name=world_name,
                run_immediately=run_immediately,
            )
        )
        self._init_script_ids.append(script_id)
        return script_id

    def remove_init_script(self, script_id: Any) -> None:
        from nodriver import cdp

        self.send_cdp(cdp.page.remove_script_to_evaluate_on_new_document(script_id))
        if script_id in self._init_script_ids:
            self._init_script_ids.remove(script_id)

    def clear_init_scripts(self) -> None:
        for script_id in list(self._init_script_ids):
            self.remove_init_script(script_id)

    def set_page_load_timeout(self, time_to_wait: float) -> None:
        self._page_load_timeout = time_to_wait

    def implicitly_wait(self, time_to_wait: float) -> None:
        self._implicit_wait = float(time_to_wait)

    def set_script_timeout(self, time_to_wait: float) -> None:
        self._script_timeout = float(time_to_wait)

    def set_auto_wait(self, timeout: float | None = None) -> None:
        self._auto_wait = True
        if timeout is not None:
            self._auto_wait_timeout = float(timeout)

    def disable_auto_wait(self) -> None:
        self._auto_wait = False

    @property
    def timeouts(self) -> Timeouts:
        return Timeouts(self)

    @property
    def session_id(self) -> str:
        return self.current_window_handle

    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "browserName": "chrome",
            "selenodriver": True,
            "pageLoadStrategy": self._page_load_strategy,
        }

    def back(self) -> None:
        self._runner.run(self._tab.back())
        self._wait_for_page_load()
        self._notify_extensions("on_context_changed")

    def forward(self) -> None:
        self._runner.run(self._tab.forward())
        self._wait_for_page_load()
        self._notify_extensions("on_context_changed")

    def refresh(self) -> None:
        self._notify_extensions("before_navigate", self.current_url)
        self._runner.run(self._tab.reload())
        self._wait_for_page_load()
        self._notify_extensions("after_navigate", self.current_url)
        self._notify_extensions("on_context_changed")

    @property
    def active_element(self) -> WebElement:
        raw = self._runner.run(self._tab.query_selector(":focus"))
        if raw is None:
            raw = self._runner.run(self._tab.query_selector("body"))
        if raw is None:
            raise NoSuchElementException("No active element found")
        return WebElement(raw, self._runner, self)

    @property
    def alert(self) -> Alert:
        return Alert(self)

    @property
    def current_window_handle(self) -> str:
        return self._window_handle_for_tab(self._tab)

    @property
    def window_handles(self) -> list[str]:
        self._update_targets()
        return self._window_handles_without_update()

    def switch_to_window(self, window_name: str) -> None:
        self._update_targets()
        for tab in getattr(self._browser, "tabs", [self._tab]):
            if self._window_handle_for_tab(tab) == window_name:
                self._tab = tab
                self._top_tab = tab
                self._frame_stack = []
                activate = getattr(tab, "activate", None) or getattr(tab, "bring_to_front", None)
                if activate is not None:
                    self._runner.run(activate())
                self._install_dialog_handler()
                self._notify_extensions("on_context_changed")
                return
        raise NoSuchWindowException(f"No window found with handle {window_name!r}")

    def switch_to_frame(self, frame_reference: Any) -> None:
        frames = self._runner.run(self._top_tab.get_frames()) if hasattr(self._top_tab, "get_frames") else []
        if isinstance(frame_reference, int):
            try:
                frame = frames[frame_reference]
            except IndexError as exc:
                raise NoSuchFrameException(f"No frame found at index {frame_reference}") from exc
        elif isinstance(frame_reference, WebElement):
            frame = getattr(frame_reference.raw, "frame", None) or getattr(frame_reference.raw, "content_frame", None)
            if frame is None:
                raise NoSuchFrameException("Frame element is not connected to a nodriver frame")
        elif isinstance(frame_reference, str):
            frame = self._find_frame_by_name_or_id(frame_reference, frames)
        else:
            frame = frame_reference
        if frame is None:
            raise NoSuchFrameException(f"No frame found for {frame_reference!r}")
        self._frame_stack.append(self._tab)
        self._tab = frame
        self._install_dialog_handler()
        self._notify_extensions("on_context_changed")

    def switch_to_default_content(self) -> None:
        self._tab = self._top_tab
        self._frame_stack = []
        self._install_dialog_handler()
        self._notify_extensions("on_context_changed")

    def switch_to_parent_frame(self) -> None:
        if self._frame_stack:
            self._tab = self._frame_stack.pop()
        else:
            self._tab = self._top_tab
        self._install_dialog_handler()
        self._notify_extensions("on_context_changed")

    def find_element(self, by: str = By.CSS_SELECTOR, value: str | None = None) -> WebElement:
        deadline = time.monotonic() + self._find_timeout()
        while True:
            elements = self.find_elements(by, value)
            if elements:
                return elements[0]
            if time.monotonic() >= deadline:
                raise NoSuchElementException(f"No element found using {by}={value!r}")
            time.sleep(0.05)

    def find_element_by_css_selector(self, css_selector: str) -> WebElement:
        return self.find_element(By.CSS_SELECTOR, css_selector)

    def find_element_by_xpath(self, xpath: str) -> WebElement:
        return self.find_element(By.XPATH, xpath)

    def find_element_by_id(self, id_: str) -> WebElement:
        return self.find_element(By.ID, id_)

    def find_element_by_name(self, name: str) -> WebElement:
        return self.find_element(By.NAME, name)

    def find_element_by_tag_name(self, name: str) -> WebElement:
        return self.find_element(By.TAG_NAME, name)

    def find_element_by_class_name(self, name: str) -> WebElement:
        return self.find_element(By.CLASS_NAME, name)

    def find_element_location(
        self,
        by: str | WebElement = By.CSS_SELECTOR,
        value: str | None = None,
        *,
        absolute: bool = False,
    ) -> dict[str, float]:
        if isinstance(by, WebElement):
            if value is not None:
                raise ValueError("value must be None when passing a WebElement")
            element = by
        else:
            element = self.find_element(by, value)
        if absolute:
            return self.find_element_absolute_location(element)
        return element.location

    def find_element_absolute_location(self, element: WebElement) -> dict[str, float]:
        window_rect = self.get_window_rect()
        element_location = element.location
        return {
            "x": window_rect["x"] + element_location["x"],
            "y": window_rect["y"] + element_location["y"],
        }

    def find_elements_by_css_selector(self, css_selector: str) -> list[WebElement]:
        return self.find_elements(By.CSS_SELECTOR, css_selector)

    def find_elements_by_xpath(self, xpath: str) -> list[WebElement]:
        return self.find_elements(By.XPATH, xpath)

    def find_elements_by_id(self, id_: str) -> list[WebElement]:
        return self.find_elements(By.ID, id_)

    def find_elements_by_name(self, name: str) -> list[WebElement]:
        return self.find_elements(By.NAME, name)

    def find_elements_by_tag_name(self, name: str) -> list[WebElement]:
        return self.find_elements(By.TAG_NAME, name)

    def find_elements_by_class_name(self, name: str) -> list[WebElement]:
        return self.find_elements(By.CLASS_NAME, name)

    def find_elements(self, by: str = By.CSS_SELECTOR, value: str | None = None) -> list[WebElement]:
        deadline = time.monotonic() + self._find_timeout()
        while True:
            elements = self._find_elements_once(by, value)
            if elements or time.monotonic() >= deadline:
                return elements
            time.sleep(0.05)

    def _find_elements_once(self, by: str = By.CSS_SELECTOR, value: str | None = None) -> list[WebElement]:
        if value is None:
            raise ValueError("value is required")
        if by == By.XPATH:
            raw_elements = self._runner.run(self._tab.xpath(value, timeout=0)) or []
        elif by == By.LINK_TEXT:
            raw = self._runner.run(self._tab.find(value, best_match=False, timeout=0))
            raw_elements = [raw] if raw else []
        elif by == By.PARTIAL_LINK_TEXT:
            raw_elements = self._runner.run(self._tab.find_all(value, timeout=0)) or []
        else:
            selector = locator_to_css(by, value)
            raw_elements = self._runner.run(self._tab.query_selector_all(selector)) or []
        return [WebElement(raw, self._runner, self) for raw in raw_elements if raw is not None]

    def execute_script(self, script: str, *args: Any) -> Any:
        if args:
            return self._normalize_script_result(self._execute_script_with_args(script, *args))
        body = script if script is not None else ""
        if re.search(r"(^|[;{}\n])\s*return\b", body):
            wrapped = f"(function(){{ {body}\n }})()"
        else:
            wrapped = f"(function(){{ return ({body}); }})()"
        return self._normalize_script_result(
            self._runner.run(self._tab.evaluate(wrapped, return_by_value=True))
        )

    @staticmethod
    def _normalize_script_result(value: Any) -> Any:
        if value is None:
            return None
        type_name = type(value).__name__
        if type_name == "ExceptionDetails":
            message = getattr(value, "text", None) or str(value)
            raise SelenoDriverException(message)
        if type_name == "RemoteObject":
            raw = getattr(value, "value", None)
            if raw is not None:
                return raw
            deep = getattr(value, "deep_serialized_value", None)
            if deep is not None and getattr(deep, "value", None) is not None:
                return deep.value
            return None
        return value

    def send_cdp(self, command: Any) -> Any:
        return self._runner.run(self._tab.send(command))

    def execute_cdp_cmd(self, cmd: str, cmd_args: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a supported Selenium-style CDP command."""
        params = cmd_args or {}
        if cmd == "Page.addScriptToEvaluateOnNewDocument":
            if "source" not in params:
                raise ValueError("source is required for Page.addScriptToEvaluateOnNewDocument")
            identifier = self.add_init_script(
                params["source"],
                run_immediately=params.get("runImmediately", True),
                world_name=params.get("worldName"),
            )
            return {"identifier": str(identifier)}
        if cmd == "Page.removeScriptToEvaluateOnNewDocument":
            from nodriver import cdp

            identifier = params.get("identifier")
            if identifier is None:
                raise ValueError("identifier is required for Page.removeScriptToEvaluateOnNewDocument")
            if not hasattr(identifier, "to_json"):
                identifier = cdp.page.ScriptIdentifier(identifier)
            self.remove_init_script(identifier)
            return {}
        raise SelenoDriverException(f"Unsupported CDP command: {cmd}")

    def scroll_to(self, x: int, y: int) -> None:
        self.execute_script(f"window.scrollTo({int(x)}, {int(y)})")

    def scroll_by(self, x: int, y: int) -> None:
        self.execute_script(f"window.scrollBy({int(x)}, {int(y)})")

    def touch_scroll_by(
        self,
        x: int = 0,
        y: int = 0,
        *,
        start_x: int | None = None,
        start_y: int | None = None,
        steps: int = 8,
    ) -> None:
        viewport = self._viewport_size()
        sx = start_x if start_x is not None else viewport["width"] // 2
        sy = start_y if start_y is not None else viewport["height"] // 2
        # Finger movement is opposite to page scroll direction.
        end_x = sx - int(x)
        end_y = sy - int(y)
        self._dispatch_touch_swipe(sx, sy, end_x, end_y, steps=steps)

    def touch_scroll_to(
        self,
        x: int,
        y: int,
        *,
        max_swipes: int = 10,
        steps: int = 8,
    ) -> None:
        for _ in range(max_swipes):
            current = self.execute_script("return {x: window.scrollX, y: window.scrollY}") or {"x": 0, "y": 0}
            dx = int(x) - int(current.get("x", 0))
            dy = int(y) - int(current.get("y", 0))
            if abs(dx) <= 2 and abs(dy) <= 2:
                return
            self.touch_scroll_by(dx, dy, steps=steps)

    def _execute_script_with_args(self, script: str, *args: Any) -> Any:
        from nodriver import cdp

        object_group = f"selenodriver-execute-script-{uuid.uuid4().hex}"
        try:
            call_args = []
            for arg in args:
                if isinstance(arg, WebElement):
                    backend_node_id = arg.raw.backend_node_id
                    if not hasattr(backend_node_id, "to_json"):
                        backend_node_id = cdp.dom.BackendNodeId(backend_node_id)
                    remote_object = self._runner.run(
                        self._tab.send(
                            cdp.dom.resolve_node(
                                backend_node_id=backend_node_id,
                                object_group=object_group,
                            )
                        )
                    )
                    object_id = getattr(remote_object, "object_id", None)
                    if object_id is None:
                        raise SelenoDriverException("Failed to resolve WebElement objectId for execute_script")
                    call_args.append(cdp.runtime.CallArgument(object_id=object_id))
                else:
                    call_args.append(cdp.runtime.CallArgument(value=arg))

            global_remote, global_errors = self._runner.run(
                self._tab.send(
                    cdp.runtime.evaluate(
                        expression="globalThis",
                        object_group=object_group,
                        return_by_value=False,
                        user_gesture=True,
                        allow_unsafe_eval_blocked_by_csp=True,
                    )
                )
            )
            if global_errors:
                raise SelenoDriverException(str(global_errors))
            global_object_id = getattr(global_remote, "object_id", None)
            if global_object_id is None:
                raise SelenoDriverException("Failed to resolve globalThis objectId for execute_script")

            function_declaration = f"function() {{ {script}\n }}"
            remote_object, errors = self._runner.run(
                self._tab.send(
                    cdp.runtime.call_function_on(
                        function_declaration,
                        object_id=global_object_id,
                        arguments=call_args,
                        return_by_value=True,
                        user_gesture=True,
                        await_promise=True,
                        object_group=object_group,
                    )
                )
            )
            if errors:
                raise SelenoDriverException(str(errors))
            return self._normalize_script_result(getattr(remote_object, "value", None))
        finally:
            try:
                self._runner.run(self._tab.send(cdp.runtime.release_object_group(object_group)))
            except Exception:
                pass

    def save_screenshot(self, filename: str) -> bool:
        self._runner.run(self._tab.save_screenshot(filename))
        return True

    get_screenshot_as_file = save_screenshot

    def get_screenshot_as_base64(self) -> str:
        return self._runner.run(self._tab.save_screenshot(as_base64=True)) or ""

    def get_screenshot_as_png(self) -> bytes:
        value = self.get_screenshot_as_base64()
        return base64.b64decode(value) if value else b""

    def get_window_size(self, window_handle: str | None = None) -> dict[str, int]:
        _window_id, bounds = self._runner.run(self._tab.get_window())
        return {"width": getattr(bounds, "width", 0), "height": getattr(bounds, "height", 0)}

    def set_window_size(self, width: int, height: int, window_handle: str | None = None) -> None:
        position = self.get_window_position(window_handle)
        self._runner.run(self._tab.set_window_size(position["x"], position["y"], width, height))

    def get_window_position(self, window_handle: str | None = None) -> dict[str, int]:
        _window_id, bounds = self._runner.run(self._tab.get_window())
        return {"x": getattr(bounds, "left", 0), "y": getattr(bounds, "top", 0)}

    def set_window_position(self, x: int, y: int, window_handle: str | None = None) -> None:
        size = self.get_window_size(window_handle)
        self._runner.run(self._tab.set_window_size(x, y, size["width"], size["height"]))

    def get_window_rect(self) -> dict[str, int]:
        return {**self.get_window_position(), **self.get_window_size()}

    def set_window_rect(
        self,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, int]:
        current = self.get_window_rect()
        next_x = current["x"] if x is None else x
        next_y = current["y"] if y is None else y
        next_width = current["width"] if width is None else width
        next_height = current["height"] if height is None else height
        self._runner.run(self._tab.set_window_size(next_x, next_y, next_width, next_height))
        return {"x": next_x, "y": next_y, "width": next_width, "height": next_height}

    def maximize_window(self) -> None:
        set_window_state = getattr(self._tab, "set_window_state", None)
        if set_window_state is not None:
            self._runner.run(set_window_state(state="maximized"))

    def minimize_window(self) -> None:
        set_window_state = getattr(self._tab, "set_window_state", None)
        if set_window_state is not None:
            self._runner.run(set_window_state(state="minimized"))

    def fullscreen_window(self) -> None:
        set_window_state = getattr(self._tab, "set_window_state", None)
        if set_window_state is not None:
            self._runner.run(set_window_state(state="fullscreen"))

    def get_cookies(self) -> list[dict[str, Any]]:
        from nodriver import cdp

        try:
            cookies = self._runner.run(self._tab.send(cdp.network.get_cookies([self.current_url]))) or []
        except Exception:
            cookies = []
        if not cookies:
            try:
                cookies = self._runner.run(self._tab.send(cdp.network.get_all_cookies())) or []
            except Exception:
                cookies = []
        if not isinstance(cookies, list):
            cookies = getattr(cookies, "cookies", None) or []
        return [self._cookie_to_dict(cookie) for cookie in cookies]

    def get_cookie(self, name: str) -> dict[str, Any] | None:
        for cookie in self.get_cookies():
            if cookie.get("name") == name:
                return cookie
        return None

    def add_cookie(self, cookie_dict: dict[str, Any]) -> None:
        from nodriver import cdp

        kwargs: dict[str, Any] = {
            "name": cookie_dict["name"],
            "value": cookie_dict["value"],
            "url": cookie_dict.get("url") or self.current_url,
            "domain": cookie_dict.get("domain"),
            "path": cookie_dict.get("path"),
            "secure": cookie_dict.get("secure"),
            "http_only": cookie_dict.get("httpOnly"),
            "expires": cookie_dict.get("expiry"),
        }
        same_site = cookie_dict.get("sameSite")
        if same_site is not None:
            kwargs["same_site"] = cdp.network.CookieSameSite(same_site)
        self._runner.run(self._tab.send(cdp.network.set_cookie(**kwargs)))

    def delete_cookie(self, name: str) -> None:
        from nodriver import cdp

        self._runner.run(self._tab.send(cdp.network.delete_cookies(name=name, url=self.current_url)))

    def delete_all_cookies(self) -> None:
        from nodriver import cdp

        self._runner.run(self._tab.send(cdp.network.clear_browser_cookies()))

    @property
    def title(self) -> str:
        script = "document.title"
        return self.execute_script(script) or ""

    @property
    def current_url(self) -> str:
        return self.execute_script("window.location.href") or ""

    @property
    def page_source(self) -> str:
        return self._runner.run(self._tab.get_content()) or ""

    def _wait_for_page_load(self) -> None:
        if self._page_load_strategy == "none":
            return
        target_state = "interactive" if self._page_load_strategy == "eager" else "complete"
        accepted = {"interactive", "complete"} if target_state == "interactive" else {"complete"}
        deadline = time.monotonic() + self._page_load_timeout
        while True:
            ready_state = self.execute_script("document.readyState")
            if not isinstance(ready_state, str):
                ready_state = str(getattr(ready_state, "value", "") or "")
            if ready_state in accepted:
                return
            if time.monotonic() >= deadline:
                raise TimeoutException(f"Timed out after {self._page_load_timeout} seconds waiting for page load")
            time.sleep(0.05)

    def _window_handle_for_tab(self, tab: Any) -> str:
        target = getattr(tab, "target", None)
        target_id = getattr(target, "target_id", None)
        if target_id is not None:
            return str(target_id)
        websocket_url = getattr(tab, "websocket_url", None)
        if websocket_url is not None:
            return str(websocket_url)
        return str(id(tab))

    def _update_targets(self) -> None:
        update_targets = getattr(self._browser, "update_targets", None)
        if update_targets is not None:
            self._runner.run(update_targets())
        self._apply_extensions_to_new_tabs()

    def _window_handles_without_update(self) -> list[str]:
        tabs = getattr(self._browser, "tabs", None)
        if tabs is None:
            tabs = [self._tab]
        return [self._window_handle_for_tab(tab) for tab in tabs]

    def _apply_extensions_to_new_tabs(self) -> None:
        tabs = getattr(self._browser, "tabs", None) or [self._tab]
        current_tab = self._tab
        current_top_tab = self._top_tab
        current_stack = list(self._frame_stack)
        try:
            for tab in tabs:
                handle = self._window_handle_for_tab(tab)
                if handle in self._known_window_handles:
                    continue
                self._known_window_handles.add(handle)
                self._tab = tab
                self._top_tab = tab
                self._frame_stack = []
                self._install_dialog_handler()
                self._notify_extensions("on_new_tab", tab, handle)
                self._notify_extensions("on_context_changed")
        finally:
            self._tab = current_tab
            self._top_tab = current_top_tab
            self._frame_stack = current_stack

    def _cookie_to_dict(self, cookie: Any) -> dict[str, Any]:
        result = {
            "name": getattr(cookie, "name", None),
            "value": getattr(cookie, "value", None),
            "domain": getattr(cookie, "domain", None),
            "path": getattr(cookie, "path", None),
            "secure": getattr(cookie, "secure", None),
            "httpOnly": getattr(cookie, "http_only", None),
        }
        expires = getattr(cookie, "expires", None)
        if expires not in (None, -1):
            result["expiry"] = expires
        same_site = getattr(cookie, "same_site", None)
        if same_site is not None:
            result["sameSite"] = getattr(same_site, "value", same_site)
        return {key: value for key, value in result.items() if value is not None}

    def _viewport_size(self) -> dict[str, int]:
        value = self.execute_script(
            "return {width: window.innerWidth || document.documentElement.clientWidth, "
            "height: window.innerHeight || document.documentElement.clientHeight}"
        )
        if isinstance(value, dict):
            return {"width": int(value.get("width", 800)), "height": int(value.get("height", 600))}
        return {"width": 800, "height": 600}

    def _dispatch_touch_swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, *, steps: int = 8) -> None:
        from nodriver import cdp

        steps = max(1, int(steps))
        start = cdp.input_.TouchPoint(x=start_x, y=start_y, radius_x=1, radius_y=1, force=1, id_=1)
        self._runner.run(self._tab.send(cdp.input_.dispatch_touch_event("touchStart", [start])))
        for index in range(1, steps + 1):
            ratio = index / steps
            x = start_x + (end_x - start_x) * ratio
            y = start_y + (end_y - start_y) * ratio
            point = cdp.input_.TouchPoint(x=x, y=y, radius_x=1, radius_y=1, force=1, id_=1)
            self._runner.run(self._tab.send(cdp.input_.dispatch_touch_event("touchMove", [point])))
        self._runner.run(self._tab.send(cdp.input_.dispatch_touch_event("touchEnd", [])))

    def _install_dialog_handler(self) -> None:
        add_handler = getattr(self._tab, "add_handler", None)
        if add_handler is None:
            return
        try:
            from nodriver import cdp
        except Exception:
            return

        add_handler(cdp.page.JavascriptDialogOpening, self._on_dialog_opening)

    def _find_timeout(self) -> float:
        return self._auto_wait_timeout if self._auto_wait else self._implicit_wait

    def _notify_extensions(self, hook_name: str, *args: Any) -> None:
        for extension in list(self._extensions):
            self._call_extension_hook(extension, hook_name, *args)

    def _call_extension_hook(self, extension: Any, hook_name: str, *args: Any) -> None:
        hook = getattr(extension, hook_name, None)
        if callable(hook):
            hook(self, *args)

    def _on_dialog_opening(self, event: Any) -> None:
        self._current_alert = event
        self._alert_prompt_text = None

    def _find_frame_by_name_or_id(self, value: str, frames: list[Any]) -> Any:
        try:
            element = self.find_element(By.CSS_SELECTOR, f'iframe[name="{value}"],iframe[id="{value}"]')
            frame = getattr(element.raw, "frame", None) or getattr(element.raw, "content_frame", None)
            if frame is not None:
                return frame
        except NoSuchElementException:
            pass
        for frame in frames:
            target = getattr(frame, "target", None)
            if str(getattr(target, "target_id", "")) == value:
                return frame
        return None

    def close(self) -> None:
        close = getattr(self._tab, "close", None)
        if close is not None:
            self._runner.run(close())
            self._update_targets()
            remaining = [tab for tab in getattr(self._browser, "tabs", []) if tab is not self._tab]
            if remaining:
                self._tab = remaining[0]

    def quit(self) -> None:
        try:
            self._notify_extensions("before_quit")
            stop = getattr(self._browser, "stop", None)
            if stop is not None:
                self._runner.run(stop())
                return
            close = getattr(self._browser, "close", None)
            if close is not None:
                self._runner.run(close())
        finally:
            if self._owns_runner:
                self._runner.close()

    @property
    def raw_browser(self) -> Any:
        return self._browser

    @property
    def raw_tab(self) -> Any:
        return self._tab
