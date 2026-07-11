from __future__ import annotations

import base64
import re

import pytest

from selenodriver import (
    ActionChains,
    Alert,
    By,
    Chrome,
    Keys,
    MobileEmulationExtension,
    MobileProfile,
    NoAlertPresentException,
    NoSuchElementException,
    NoSuchFrameException,
    NoSuchWindowException,
    Options,
    TimeoutException,
    WebDriverWait,
    WebElement,
)
from selenodriver import expected_conditions as EC


class ImmediateRunner:
    def run(self, value):
        return value


class FakeElement:
    def __init__(
        self,
        text="",
        attrs=None,
        rect=None,
        displayed=True,
        enabled=True,
        tag_name="div",
        properties=None,
        css=None,
        selected=False,
    ):
        self.text = text
        self.attrs = attrs or {}
        self.tag_name = tag_name
        self.properties = properties or {}
        self.css = css or {}
        self.selected = selected
        self.shadow_roots = []
        self.rect = rect or {"height": 20, "width": 100, "x": 10, "y": 15}
        self.displayed = displayed
        self.enabled = enabled
        self.clicked = False
        self.keys = ""
        self.cleared = False
        self.moved = False
        self.dragged_to = None
        self.focused = False
        self.applied_scripts = []
        self.backend_node_id = id(self)
        self.xpath_queries = {}
        self._xpath_marked = {}
        self._xpath_self_marked = set()

    def click(self):
        self.clicked = True

    def mouse_click(self, **kwargs):
        self.clicked = kwargs or True

    def mouse_move(self):
        self.moved = True

    def mouse_drag(self, destination, relative=False):
        self.dragged_to = (destination, relative)

    def send_keys(self, text):
        self.keys += text

    def focus(self):
        self.focused = True

    def clear_input(self):
        self.cleared = True

    def query_selector_all(self, selector):
        prefix = '[data-selenodriver-xpath="'
        if selector.startswith(prefix) and selector.endswith('"]'):
            token = selector[len(prefix) : -2]
            return self._xpath_marked.get(token, [])
        return []

    def apply(self, script, **_kwargs):
        self.applied_scripts.append(script)
        if "document.evaluate" in script:
            for xpath, elements in self.xpath_queries.items():
                if repr(xpath) in script:
                    match = re.search(r"node\.setAttribute\('data-selenodriver-xpath', '([^']+)'\)", script)
                    token = match.group(1) if match else None
                    if token is not None:
                        self._xpath_marked[token] = [element for element in elements if element is not self]
                        if self in elements:
                            self._xpath_self_marked.add(token)
                    return len(elements)
            return 0
        if "removeAttribute('data-selenodriver-xpath')" in script:
            for token in list(self._xpath_marked):
                if token in script:
                    self._xpath_marked.pop(token, None)
            for token in list(self._xpath_self_marked):
                if token in script:
                    self._xpath_self_marked.remove(token)
            return True
        if "el.getAttribute('data-selenodriver-xpath')" in script:
            for token in self._xpath_self_marked:
                if token in script:
                    return True
            return False
        if "getBoundingClientRect" in script and "height:" in script:
            return self.rect
        if "toDataURL" in script:
            return base64.b64encode(b"element-png").decode()
        if "tagName.toLowerCase" in script:
            return self.tag_name
        if "Array.from(el.options).map" in script:
            return [{"index": 0, "text": "Korea", "value": "kr", "selected": True, "disabled": False}]
        if "window.getComputedStyle(el).getPropertyValue" in script:
            if "'display'" in script or '"display"' in script:
                return self.css.get("display", "block")
            return ""
        if "el[" in script:
            for key, value in self.properties.items():
                if repr(key) in script:
                    return value
            return None
        if "el.checked || el.selected" in script:
            return self.selected
        if "requestSubmit" in script or "scrollIntoView" in script:
            return True
        if "window.getComputedStyle" in script:
            return self.displayed
        if "aria-disabled" in script:
            return self.enabled
        return True


class FakeTarget:
    def __init__(self, target_id):
        self.target_id = target_id


class FakeTab:
    def __init__(self, target_id="tab-1"):
        self.target = FakeTarget(target_id)
        self.queries = {}
        self.xpath_queries = {}
        self.sent = []
        self.navigation_calls = []
        self.ready_state = "complete"
        self.activated = False
        self.closed = False
        self.handlers = {}
        self.dialog_commands = []
        self.script_commands = []
        self.cookies = []
        self.url_cookies = None
        self.frames = []
        self.delayed_queries = {}
        self.focused_element = None
        self.window_rect = {"left": 10, "top": 20, "width": 800, "height": 600}
        self.window_state = "normal"
        self.evaluated_scripts = []
        self.scroll_position = {"x": 0, "y": 0}
        self.cdp_methods = []
        self.cdp_requests = []

    def query_selector_all(self, selector):
        if selector in self.delayed_queries:
            values = self.delayed_queries[selector]
            return values.pop(0) if values else []
        return self.queries.get(selector, [])

    def query_selector(self, selector):
        if selector == ":focus":
            return self.focused_element
        values = self.query_selector_all(selector)
        return values[0] if values else None

    def xpath(self, xpath, timeout=0):
        return self.xpath_queries.get(xpath, [])

    def evaluate(self, script, return_by_value=True):
        self.evaluated_scripts.append(script)
        if "document.title" in script:
            return "Fake title"
        if "window.location.href" in script:
            return "https://example.test/"
        if "document.readyState" in script:
            return self.ready_state
        if "return 1" in script:
            return 1
        if "const value = 2; return value" in script:
            return 2
        if "window.innerWidth" in script:
            return {"width": 400, "height": 800}
        if "window.scrollX" in script:
            return self.scroll_position
        return "result"

    def get_content(self):
        return "<html></html>"

    def save_screenshot(self, filename="auto", format="jpeg", full_page=False, as_base64=False):
        if as_base64:
            return base64.b64encode(b"png").decode()
        return filename

    def send(self, event):
        self.sent.append(event)
        if "handleJavaScriptDialog" in repr(event):
            self.dialog_commands.append(event)
        if hasattr(event, "send"):
            try:
                request = next(event)
                method = request.get("method", "")
                self.cdp_methods.append(method)
                self.cdp_requests.append(request)
                if method == "DOM.resolveNode":
                    from nodriver import cdp

                    return type("RemoteObject", (), {"object_id": cdp.runtime.RemoteObjectId("remote-1")})()
                if method == "Runtime.callFunctionOn":
                    self.script_commands.append(request)
                    return (type("RemoteObject", (), {"value": "script-result"})(), None)
                if method == "Network.getCookies":
                    return self.cookies if self.url_cookies is None else self.url_cookies
                if method == "Network.getAllCookies":
                    return self.cookies
                if method == "Network.setCookie":
                    self.cookies.append(
                        type(
                            "Cookie",
                            (),
                            {
                                "name": request["params"]["name"],
                                "value": request["params"]["value"],
                                "domain": request["params"].get("domain", "example.test"),
                                "path": request["params"].get("path", "/"),
                                "secure": request["params"].get("secure", False),
                                "http_only": request["params"].get("httpOnly", False),
                                "expires": request["params"].get("expires", -1),
                                "same_site": request["params"].get("sameSite"),
                            },
                        )()
                    )
                    return True
                if method == "Network.deleteCookies":
                    name = request["params"]["name"]
                    self.cookies = [cookie for cookie in self.cookies if cookie.name != name]
                    return None
                if method == "Network.clearBrowserCookies":
                    self.cookies = []
                    return None
                if method == "Fake.command":
                    return "cdp-result"
                if method == "Page.addScriptToEvaluateOnNewDocument":
                    from nodriver import cdp

                    return cdp.page.ScriptIdentifier("script-id-1")
                if method == "Page.removeScriptToEvaluateOnNewDocument":
                    return None
            except StopIteration:
                return None

    def back(self):
        self.navigation_calls.append("back")

    def forward(self):
        self.navigation_calls.append("forward")

    def reload(self):
        self.navigation_calls.append("reload")

    def activate(self):
        self.activated = True

    def close(self):
        self.closed = True

    def add_handler(self, event_type, callback):
        self.handlers.setdefault(event_type, []).append(callback)

    def get_frames(self):
        return self.frames

    def get_window(self):
        bounds = type(
            "Bounds",
            (),
            {
                "left": self.window_rect["left"],
                "top": self.window_rect["top"],
                "width": self.window_rect["width"],
                "height": self.window_rect["height"],
            },
        )()
        return 1, bounds

    def set_window_size(self, left=0, top=0, width=1280, height=1024):
        self.window_rect = {"left": left, "top": top, "width": width, "height": height}

    def set_window_state(self, left=0, top=0, width=1280, height=720, state="normal"):
        self.window_state = state


class FakeDialog:
    def __init__(self, message="hello"):
        self.message = message


class FakeCdpCommand:
    def __init__(self):
        self._sent = False

    def __iter__(self):
        return self

    def __next__(self):
        if self._sent:
            raise StopIteration
        self._sent = True
        return {"method": "Fake.command", "params": {}}

    def send(self, _value):
        raise StopIteration("cdp-result")


class FakeBrowser:
    def __init__(self, tab, tabs=None):
        self.main_tab = tab
        self.tabs = tabs or [tab]
        self.last_url = None
        self.stopped = False
        self.update_count = 0
        self.pending_tabs = []

    def get(self, url):
        self.last_url = url
        return self.main_tab

    def stop(self):
        self.stopped = True

    def update_targets(self):
        self.update_count += 1
        if self.pending_tabs:
            self.tabs.extend(self.pending_tabs)
            self.pending_tabs = []


class FakeExtension:
    def __init__(self):
        self.events = []

    def on_attach(self, driver):
        self.events.append(("attach", driver.current_window_handle))

    def before_navigate(self, driver, url):
        self.events.append(("before", url))

    def after_navigate(self, driver, url):
        self.events.append(("after", url))

    def on_context_changed(self, driver):
        self.events.append(("context", driver.current_window_handle))

    def before_quit(self, driver):
        self.events.append(("quit", driver.current_window_handle))

    def on_new_tab(self, driver, tab, handle):
        self.events.append(("new_tab", handle, tab is driver.raw_tab))


@pytest.fixture()
def driver():
    tab = FakeTab()
    browser = FakeBrowser(tab)
    return Chrome(browser=browser, tab=tab, runner=ImmediateRunner())


def test_get_uses_browser_navigation(driver):
    driver.get("https://example.test")
    assert driver.raw_browser.last_url == "https://example.test"


def test_extension_hooks_and_init_scripts():
    tab = FakeTab()
    browser = FakeBrowser(tab)
    extension = FakeExtension()
    driver = Chrome(browser=browser, tab=tab, runner=ImmediateRunner(), extensions=[extension])

    script_id = driver.add_init_script("window.__x = 1")
    driver.get("https://example.test")
    driver.refresh()
    driver.remove_init_script(script_id)
    driver.quit()

    assert script_id == "script-id-1"
    assert ("attach", "tab-1") in extension.events
    assert ("before", "https://example.test") in extension.events
    assert ("after", "https://example.test") in extension.events
    assert ("quit", "tab-1") in extension.events


def test_mobile_emulation_extension_applies_cdp_commands():
    tab = FakeTab()
    browser = FakeBrowser(tab)
    profile = MobileProfile(
        name="Test Phone",
        user_agent="Mozilla/5.0 Test Mobile",
        platform="Android",
        width=390,
        height=844,
        device_scale_factor=3,
        locale="ko-KR",
        timezone_id="Asia/Seoul",
    )
    extension = MobileEmulationExtension(profile)

    driver = Chrome(browser=browser, tab=tab, runner=ImmediateRunner(), extensions=[extension])
    driver.get("https://example.test")

    assert "Emulation.setUserAgentOverride" in tab.cdp_methods
    assert "Emulation.setDeviceMetricsOverride" in tab.cdp_methods
    assert "Emulation.setTouchEmulationEnabled" in tab.cdp_methods
    assert "Emulation.setLocaleOverride" in tab.cdp_methods
    assert "Emulation.setTimezoneOverride" in tab.cdp_methods
    assert tab.cdp_methods.count("Emulation.setLocaleOverride") == 1
    assert tab.cdp_methods.count("Emulation.setTimezoneOverride") == 1


def test_mobile_emulation_profile_shortcuts_are_deterministic_with_seed():
    android = MobileEmulationExtension("android", seed=1)
    ios = MobileEmulationExtension("ios", seed=1)

    assert android.profile.platform == "Android"
    assert ios.profile.platform == "iPhone"


def test_mobile_emulation_accepts_user_profile_format():
    extension = MobileEmulationExtension(
        {
            "device_name": "iPhone 16 Pro",
            "os_type": "ios",
            "width": 402,
            "height": 874,
            "devicePixelRatio": 3.0,
            "UA": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
            "platform": "iPhone",
            "language": "ko-KR",
            "languages": ["ko-KR", "ko"],
        }
    )

    assert extension.profile.name == "iPhone 16 Pro"
    assert extension.profile.os_type == "ios"
    assert extension.profile.user_agent.startswith("Mozilla/5.0")
    assert extension.profile.device_scale_factor == 3.0
    assert extension.profile.locale == "ko-KR"
    assert extension.profile.languages == ["ko-KR", "ko"]
    assert extension._accept_language() == "ko-KR,ko"


def test_use_extension_callable():
    tab = FakeTab()
    browser = FakeBrowser(tab)
    calls = []
    driver = Chrome(browser=browser, tab=tab, runner=ImmediateRunner())

    driver.use(lambda d: calls.append(d.current_window_handle))

    assert calls == ["tab-1"]


def test_new_tab_detection_applies_extension():
    tab1 = FakeTab("tab-1")
    tab2 = FakeTab("tab-2")
    browser = FakeBrowser(tab1, [tab1])
    browser.pending_tabs = [tab2]
    extension = FakeExtension()
    driver = Chrome(browser=browser, tab=tab1, runner=ImmediateRunner(), extensions=[extension])

    assert driver.window_handles == ["tab-1", "tab-2"]

    assert ("new_tab", "tab-2", True) in extension.events
    assert driver.raw_tab is tab1


def test_get_waits_for_document_ready_state(driver):
    driver.raw_tab.ready_state = "loading"
    driver.set_page_load_timeout(0.01)

    with pytest.raises(TimeoutException):
        driver.get("https://example.test")


def test_get_can_skip_page_load_wait():
    tab = FakeTab()
    tab.ready_state = "loading"
    browser = FakeBrowser(tab)
    driver = Chrome(browser=browser, tab=tab, runner=ImmediateRunner(), page_load_strategy="none")

    driver.get("https://example.test")

    assert browser.last_url == "https://example.test"


def test_options_to_nodriver_kwargs():
    options = Options()
    options.add_argument("--no-first-run")
    options.add_arguments("--disable-sync", "--disable-default-apps")
    options.binary_location = "C:/Chrome/chrome.exe"
    options.headless = True
    options.set_user_data_dir("profile")
    options.lang = "ko-KR"
    options.add_experimental_option("prefs", {"download.default_directory": "downloads"})

    assert options.to_nodriver_kwargs() == {
        "browser_args": ["--no-first-run", "--disable-sync", "--disable-default-apps"],
        "browser_executable_path": "C:/Chrome/chrome.exe",
        "headless": True,
        "user_data_dir": "profile",
        "lang": "ko-KR",
        "prefs": {"download.default_directory": "downloads"},
    }
    assert options.capabilities["goog:chromeOptions"]["args"][0] == "--no-first-run"


def test_options_extracts_user_data_dir_argument():
    options = Options()
    options.add_arguments("--no-first-run", "--user-data-dir=C:/profiles/test")

    assert options.to_nodriver_kwargs() == {
        "browser_args": ["--no-first-run"],
        "user_data_dir": "C:/profiles/test",
    }


def test_chrome_passes_options_to_nodriver(monkeypatch):
    import nodriver

    captured = {}
    tab = FakeTab()
    browser = FakeBrowser(tab)
    options = Options()
    options.add_argument("--no-first-run")

    def fake_start(**kwargs):
        captured.update(kwargs)
        return browser

    monkeypatch.setattr(nodriver, "start", fake_start)

    driver = Chrome(options=options, runner=ImmediateRunner(), page_load_strategy="none")

    assert driver.raw_browser is browser
    assert captured["browser_args"] == ["--no-first-run"]


def test_chrome_options_import_paths():
    from selenodriver import ChromeOptions
    from selenodriver.webdriver.chrome.options import Options as CompatOptions

    assert ChromeOptions is Options
    assert CompatOptions is Options


def test_navigation_helpers(driver):
    driver.back()
    driver.forward()
    driver.refresh()

    assert driver.raw_tab.navigation_calls == ["back", "forward", "reload"]


def test_session_capabilities_timeouts_and_script_timeout(driver):
    driver.implicitly_wait(1.5)
    driver.set_page_load_timeout(7)
    driver.set_script_timeout(9)

    assert driver.session_id == "tab-1"
    assert driver.capabilities["browserName"] == "chrome"
    assert driver.timeouts.implicit_wait == 1.5
    assert driver.timeouts.page_load == 7
    assert driver.timeouts.script == 9


def test_scroll_helpers(driver):
    driver.scroll_to(10, 20)
    driver.scroll_by(1, 2)

    assert any("window.scrollTo(10, 20)" in script for script in driver.raw_tab.evaluated_scripts)
    assert any("window.scrollBy(1, 2)" in script for script in driver.raw_tab.evaluated_scripts)


def test_touch_scroll_by_dispatches_touch_events(driver):
    driver.touch_scroll_by(0, 300, steps=3)

    assert len(driver.raw_tab.sent) == 5


def test_touch_scroll_to_stops_when_position_matches(driver):
    driver.raw_tab.scroll_position = {"x": 0, "y": 300}

    driver.touch_scroll_to(0, 300)

    assert driver.raw_tab.sent == []


def test_execute_script_with_element_and_value_args(driver):
    raw = FakeElement()
    element = WebElement(raw, driver._runner, driver)

    result = driver.execute_script("return arguments[0].textContent + arguments[1];", element, "x")

    assert result == "script-result"
    assert driver.raw_tab.script_commands


def test_execute_script_supports_return_and_expression_styles(driver):
    assert driver.execute_script("return 1") == 1
    assert driver.execute_script("const value = 2; return value") == 2
    assert driver.execute_script("document.readyState") == "complete"


def test_execute_script_normalizes_remote_objects_and_errors():
    remote = type("RemoteObject", (), {"value": "complete"})()
    error = type("ExceptionDetails", (), {"text": "bad script"})()

    assert Chrome._normalize_script_result(remote) == "complete"
    with pytest.raises(Exception, match="bad script"):
        Chrome._normalize_script_result(error)


def test_send_cdp_helpers(driver):
    assert driver.send_cdp(FakeCdpCommand()) == "cdp-result"

    element = WebElement(FakeElement(), driver._runner, driver)
    assert element.send_cdp(FakeCdpCommand()) == "cdp-result"


def test_execute_cdp_cmd_adds_and_removes_init_script(driver):
    result = driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "window.__x = 1"},
    )
    driver.execute_cdp_cmd(
        "Page.removeScriptToEvaluateOnNewDocument",
        {"identifier": result["identifier"]},
    )

    assert result == {"identifier": "script-id-1"}
    assert "Page.addScriptToEvaluateOnNewDocument" in driver.raw_tab.cdp_methods
    assert "Page.removeScriptToEvaluateOnNewDocument" in driver.raw_tab.cdp_methods


def test_execute_cdp_cmd_rejects_unknown_command(driver):
    with pytest.raises(Exception, match="Unsupported CDP command"):
        driver.execute_cdp_cmd("Network.unknown", {})


def test_cookie_api(driver):
    driver.add_cookie({"name": "session", "value": "abc", "path": "/", "secure": True})

    assert driver.get_cookie("session")["value"] == "abc"
    assert driver.get_cookies()[0]["secure"] is True

    driver.delete_cookie("session")
    assert driver.get_cookie("session") is None

    driver.add_cookie({"name": "a", "value": "1"})
    driver.delete_all_cookies()
    assert driver.get_cookies() == []


def test_get_cookies_falls_back_to_all_browser_cookies(driver):
    cookie = type(
        "Cookie",
        (),
        {
            "name": "NID_AUT",
            "value": "token",
            "domain": ".naver.com",
            "path": "/",
            "secure": True,
            "http_only": True,
            "expires": -1,
            "same_site": None,
        },
    )()
    driver.raw_tab.url_cookies = []
    driver.raw_tab.cookies = [cookie]

    assert driver.get_cookies()[0]["name"] == "NID_AUT"
    assert driver.raw_tab.cdp_methods[-2:] == ["Network.getCookies", "Network.getAllCookies"]


def test_driver_screenshot_api(driver):
    assert driver.save_screenshot("screen.png") is True
    assert driver.get_screenshot_as_file("screen.png") is True
    assert driver.get_screenshot_as_png() == b"png"
    assert driver.get_screenshot_as_base64() == base64.b64encode(b"png").decode()


def test_window_rect_size_position_and_state(driver):
    assert driver.get_window_size() == {"width": 800, "height": 600}
    assert driver.get_window_position() == {"x": 10, "y": 20}
    assert driver.get_window_rect() == {"x": 10, "y": 20, "width": 800, "height": 600}

    driver.set_window_size(1024, 768)
    assert driver.get_window_size() == {"width": 1024, "height": 768}

    driver.set_window_position(30, 40)
    assert driver.get_window_position() == {"x": 30, "y": 40}

    assert driver.set_window_rect(x=1, y=2, width=3, height=4) == {"x": 1, "y": 2, "width": 3, "height": 4}
    driver.maximize_window()
    assert driver.raw_tab.window_state == "maximized"
    driver.minimize_window()
    assert driver.raw_tab.window_state == "minimized"
    driver.fullscreen_window()
    assert driver.raw_tab.window_state == "fullscreen"


def test_active_element(driver):
    raw = FakeElement("focused")
    driver.raw_tab.focused_element = raw

    assert driver.switch_to.active_element.text == "focused"


def test_element_screenshot_api(driver, tmp_path):
    raw = FakeElement()
    element = WebElement(raw, driver._runner, driver)
    target = tmp_path / "element.png"

    assert element.screenshot(str(target)) is True
    assert element.screenshot_as_png == b"element-png"
    assert target.read_bytes() == b"element-png"


def test_element_property_css_and_selected():
    raw = FakeElement(
        attrs={"id": "field"},
        properties={"value": "abc"},
        css={"display": "inline-block"},
        selected=True,
    )
    element = WebElement(raw, ImmediateRunner())

    assert element.get_dom_attribute("id") == "field"
    assert element.get_property("value") == "abc"
    assert element.value_of_css_property("display") == "inline-block"
    assert element.is_selected() is True


def test_element_submit_scroll_and_shadow_root():
    raw_child = FakeElement("shadow child")

    class FakeShadowRoot:
        def query_selector_all(self, selector):
            return [raw_child] if selector == "button" else []

    raw = FakeElement()
    raw.shadow_roots = [FakeShadowRoot()]
    element = WebElement(raw, ImmediateRunner())

    element.submit()
    element.scroll_into_view()

    assert element.shadow_root.find_element(By.TAG_NAME, "button").text == "shadow child"


def test_element_touch_scroll_into_view(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 1000})
    element = WebElement(raw, driver._runner, driver)

    element.touch_scroll_into_view(max_swipes=1, steps=2)

    assert len(driver.raw_tab.sent) == 4


def test_window_handles_and_switch_to_window():
    tab1 = FakeTab("tab-1")
    tab2 = FakeTab("tab-2")
    browser = FakeBrowser(tab1, [tab1, tab2])
    driver = Chrome(browser=browser, tab=tab1, runner=ImmediateRunner())

    assert driver.current_window_handle == "tab-1"
    assert driver.window_handles == ["tab-1", "tab-2"]

    driver.switch_to.window("tab-2")

    assert driver.current_window_handle == "tab-2"
    assert tab2.activated is True


def test_switch_to_frame_by_index_and_back(driver):
    frame = FakeTab("frame-1")
    driver.raw_tab.frames = [frame]

    driver.switch_to.frame(0)
    assert driver.raw_tab is frame

    driver.switch_to.parent_frame()
    assert driver.raw_tab is driver._top_tab

    driver.switch_to.frame(0)
    driver.switch_to.default_content()
    assert driver.raw_tab is driver._top_tab


def test_switch_to_missing_frame_raises(driver):
    with pytest.raises(NoSuchFrameException):
        driver.switch_to.frame(3)


def test_window_handles_updates_targets():
    tab1 = FakeTab("tab-1")
    tab2 = FakeTab("tab-2")
    browser = FakeBrowser(tab1, [tab1])
    browser.pending_tabs = [tab2]
    driver = Chrome(browser=browser, tab=tab1, runner=ImmediateRunner())

    assert driver.window_handles == ["tab-1", "tab-2"]
    assert browser.update_count == 1


def test_switch_to_missing_window_raises(driver):
    with pytest.raises(NoSuchWindowException):
        driver.switch_to.window("missing")


def test_close_closes_current_tab():
    tab1 = FakeTab("tab-1")
    tab2 = FakeTab("tab-2")
    browser = FakeBrowser(tab1, [tab1, tab2])
    driver = Chrome(browser=browser, tab=tab1, runner=ImmediateRunner())

    driver.close()

    assert tab1.closed is True
    assert driver.current_window_handle == "tab-2"


def test_find_element_by_css(driver):
    raw = FakeElement("hello", {"href": "/x"})
    driver.raw_tab.queries["h1"] = [raw]

    element = driver.find_element(By.CSS_SELECTOR, "h1")

    assert element.text == "hello"
    assert element.get_attribute("href") == "/x"


def test_legacy_find_element_aliases(driver):
    raw = FakeElement("hello")
    driver.raw_tab.queries[".item"] = [raw]
    driver.raw_tab.queries["#item"] = [raw]
    driver.raw_tab.queries["div"] = [raw]
    driver.raw_tab.queries[".card"] = [raw]
    driver.raw_tab.queries['[name="q"]'] = [raw]
    driver.raw_tab.xpath_queries["//div"] = [raw]

    assert driver.find_element_by_css_selector(".item").text == "hello"
    assert driver.find_element_by_id("item").text == "hello"
    assert driver.find_element_by_name("q").text == "hello"
    assert driver.find_element_by_tag_name("div").text == "hello"
    assert driver.find_element_by_class_name("card").text == "hello"
    assert driver.find_element_by_xpath("//div").text == "hello"
    assert driver.find_elements_by_css_selector(".item")
    assert driver.find_elements_by_xpath("//div")


def test_implicitly_wait_polls_until_element_found(driver):
    raw = FakeElement("late")
    driver.raw_tab.delayed_queries[".late"] = [[], [raw]]
    driver.implicitly_wait(0.2)

    assert driver.find_element(By.CSS_SELECTOR, ".late").text == "late"


def test_auto_wait_is_off_by_default(driver):
    driver.raw_tab.delayed_queries[".late"] = [[], [FakeElement("late")]]

    with pytest.raises(NoSuchElementException):
        driver.find_element(By.CSS_SELECTOR, ".late")


def test_auto_wait_polls_find_element_when_enabled(driver):
    raw = FakeElement("late")
    driver.raw_tab.delayed_queries[".late"] = [[], [raw]]
    driver.set_auto_wait(0.2)

    assert driver.find_element(By.CSS_SELECTOR, ".late").text == "late"


def test_auto_wait_can_be_disabled(driver):
    driver.set_auto_wait(0.2)
    driver.disable_auto_wait()
    driver.raw_tab.delayed_queries[".late"] = [[], [FakeElement("late")]]

    with pytest.raises(NoSuchElementException):
        driver.find_element(By.CSS_SELECTOR, ".late")


def test_auto_wait_action_waits_until_element_ready(driver):
    raw = FakeElement(displayed=False)
    calls = {"count": 0}

    def is_displayed():
        calls["count"] += 1
        raw.displayed = calls["count"] > 1
        return raw.displayed

    driver.set_auto_wait(0.2)
    element = WebElement(raw, driver._runner, driver)
    element.is_displayed = is_displayed

    element.click()

    assert calls["count"] >= 2


def test_js_click_does_not_apply_auto_wait(driver):
    raw = FakeElement(displayed=False)
    driver.set_auto_wait(0.01)
    element = WebElement(raw, driver._runner, driver)

    element.js_click()

    assert "(el) => el.click()" in raw.applied_scripts


def test_locator_conversion(driver):
    raw = FakeElement("submit")
    driver.raw_tab.queries['[name="submit"]'] = [raw]

    assert driver.find_element(By.NAME, "submit").text == "submit"


def test_find_element_by_xpath(driver):
    raw = FakeElement("from xpath")
    driver.raw_tab.xpath_queries["//h1"] = [raw]

    assert driver.find_element(By.XPATH, "//h1").text == "from xpath"


def test_element_find_element_by_xpath(driver):
    parent = FakeElement()
    child = FakeElement("nested xpath", tag_name="button")
    parent.xpath_queries[".//button"] = [child]
    element = WebElement(parent, driver._runner, driver)

    found = element.find_element(By.XPATH, ".//button")

    assert found.text == "nested xpath"
    assert parent._xpath_marked == {}


def test_element_find_element_by_xpath_can_return_self(driver):
    parent = FakeElement("self")
    parent.xpath_queries["."] = [parent]
    element = WebElement(parent, driver._runner, driver)

    found = element.find_element(By.XPATH, ".")

    assert found.raw is parent
    assert parent._xpath_marked == {}
    assert parent._xpath_self_marked == set()


def test_missing_element_raises(driver):
    with pytest.raises(NoSuchElementException):
        driver.find_element(By.CSS_SELECTOR, ".missing")


def test_element_actions(driver):
    raw = FakeElement()
    driver.raw_tab.queries["input"] = [raw]

    element = driver.find_element(By.CSS_SELECTOR, "input")
    element.send_keys("a", "b")
    element.click()
    element.clear()

    assert raw.keys == "ab"
    assert len(driver.raw_tab.sent) == 2
    assert raw.cleared is True


def test_element_click_uses_center_coordinate_events(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15})
    driver.raw_tab.queries["button"] = [raw]

    element = driver.find_element(By.CSS_SELECTOR, "button")
    element.click()

    assert len(driver.raw_tab.sent) == 2


def test_element_touch_click_uses_touch_events(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15})
    driver.raw_tab.queries["button"] = [raw]

    element = driver.find_element(By.CSS_SELECTOR, "button")
    element.click(input_type="touch")

    assert len(driver.raw_tab.sent) == 2


def test_element_click_can_use_touch_alias(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15})
    driver.raw_tab.queries["button"] = [raw]

    element = driver.find_element(By.CSS_SELECTOR, "button")
    element.click(use_touch=True)

    assert len(driver.raw_tab.sent) == 2


def test_element_js_click_uses_element_click_script(driver):
    raw = FakeElement()
    driver.raw_tab.queries["button"] = [raw]

    element = driver.find_element(By.CSS_SELECTOR, "button")
    element.js_click()

    assert "(el) => el.click()" in raw.applied_scripts


def test_element_size_location_and_rect(driver):
    raw = FakeElement(rect={"height": 25.5, "width": 120, "x": 7, "y": 9})
    driver.raw_tab.queries["button"] = [raw]

    element = driver.find_element(By.CSS_SELECTOR, "button")
    element_size = element.size
    element_width = element_size["width"]
    element_height = element_size["height"]

    assert element_width == 120
    assert element_height == 25.5
    assert element.location == {"x": 7, "y": 9}
    assert element.rect == {"height": 25.5, "width": 120, "x": 7, "y": 9}
    assert driver.find_element_location(By.CSS_SELECTOR, "button") == {"x": 7, "y": 9}
    assert driver.find_element_location(element) == {"x": 7, "y": 9}
    assert driver.find_element_absolute_location(element) == {"x": 17, "y": 29}
    assert driver.find_element_location(element, absolute=True) == {"x": 17, "y": 29}


def test_wait_expected_condition(driver):
    raw = FakeElement("ready")
    driver.raw_tab.queries[".ready"] = [raw]

    element = WebDriverWait(driver, 0.1, poll_frequency=0.01).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".ready"))
    )

    assert element.text == "ready"


def test_wait_ignores_missing_element_by_default(driver):
    with pytest.raises(TimeoutException):
        WebDriverWait(driver, 0.01, poll_frequency=0.01).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".missing"))
        )


def test_expected_conditions_title_url_and_text(driver):
    raw = FakeElement("hello world", {"value": "ready"})
    driver.raw_tab.queries[".message"] = [raw]

    assert EC.title_is("Fake title")(driver) is True
    assert EC.title_contains("title")(driver) is True
    assert EC.url_contains("example")(driver) is True
    assert EC.url_to_be("https://example.test/")(driver) is True
    assert EC.url_matches(r"example\.test")(driver) is True
    assert EC.text_to_be_present_in_element((By.CSS_SELECTOR, ".message"), "world")(driver) is True
    assert EC.text_to_be_present_in_element_value((By.CSS_SELECTOR, ".message"), "ready")(driver) is True


def test_expected_conditions_visibility_clickable_and_invisibility(driver):
    visible = FakeElement("visible", displayed=True, enabled=True)
    hidden = FakeElement("hidden", displayed=False, enabled=True)
    disabled = FakeElement("disabled", displayed=True, enabled=False)
    driver.raw_tab.queries[".visible"] = [visible]
    driver.raw_tab.queries[".hidden"] = [hidden]
    driver.raw_tab.queries[".disabled"] = [disabled]

    assert EC.visibility_of_element_located((By.CSS_SELECTOR, ".visible"))(driver)
    assert EC.element_to_be_clickable((By.CSS_SELECTOR, ".visible"))(driver)
    assert EC.element_to_be_clickable((By.CSS_SELECTOR, ".disabled"))(driver) is False
    assert EC.invisibility_of_element_located((By.CSS_SELECTOR, ".hidden"))(driver) is True


def test_expected_conditions_window_count(driver):
    tab2 = FakeTab("tab-2")
    driver.raw_browser.pending_tabs = [tab2]

    assert EC.number_of_windows_to_be(2)(driver) is True
    assert EC.new_window_is_opened(["tab-1"])(driver) is True


def test_alert_is_present_and_accept(driver):
    driver._on_dialog_opening(FakeDialog("confirm?"))

    alert = EC.alert_is_present()(driver)

    assert isinstance(alert, Alert)
    assert alert.text == "confirm?"
    alert.accept()
    assert driver._current_alert is None
    assert driver.raw_tab.sent


def test_alert_send_keys_and_dismiss(driver):
    driver._on_dialog_opening(FakeDialog("prompt"))

    alert = driver.switch_to.alert
    alert.send_keys("answer")
    alert.dismiss()

    assert driver._current_alert is None
    assert driver._alert_prompt_text is None
    assert driver.raw_tab.sent


def test_alert_is_present_returns_false_without_dialog(driver):
    assert EC.alert_is_present()(driver) is False


def test_switch_to_alert_raises_without_dialog(driver):
    with pytest.raises(NoAlertPresentException):
        _ = driver.switch_to.alert


def test_support_import_paths():
    from selenodriver.support import expected_conditions as support_ec
    from selenodriver.support.select import Select
    from selenodriver.support.ui import WebDriverWait as SupportWait

    assert SupportWait is WebDriverWait
    assert support_ec.title_is("x") is not None
    assert Select is not None


def test_selenium_compatible_import_paths():
    from selenodriver.webdriver.common.action_chains import ActionChains as CompatActionChains
    from selenodriver.webdriver.common.by import By as CompatBy
    from selenodriver.webdriver.common.keys import Keys as CompatKeys
    from selenodriver.webdriver.remote.webelement import WebElement as CompatWebElement
    from selenodriver.webdriver.support import expected_conditions as compat_ec
    from selenodriver.webdriver.support.ui import Select as CompatSelect
    from selenodriver.webdriver.support.ui import WebDriverWait as CompatWait

    assert CompatActionChains is ActionChains
    assert CompatBy is By
    assert CompatKeys is Keys
    assert CompatWebElement is WebElement
    assert CompatWait is WebDriverWait
    assert CompatSelect is not None
    assert compat_ec.alert_is_present is not None


def test_select_support():
    from selenodriver.support.select import Select

    raw = FakeElement(attrs={"multiple": "multiple"}, tag_name="select")
    element = WebElement(raw, ImmediateRunner())
    select = Select(element)

    assert select.is_multiple is True
    assert select.options[0]["value"] == "kr"
    assert select.first_selected_option["text"] == "Korea"
    select.select_by_value("kr")
    select.select_by_visible_text("Korea")
    select.select_by_index(0)
    select.deselect_all()


def test_select_rejects_non_select_element():
    from selenodriver.support.select import Select

    with pytest.raises(ValueError):
        Select(WebElement(FakeElement(tag_name="input"), ImmediateRunner()))


def test_action_chains_element_actions(driver):
    source = FakeElement("source")
    target = FakeElement("target")
    source_element = WebElement(source, driver._runner)
    target_element = WebElement(target, driver._runner)

    ActionChains(driver).move_to_element(source_element).click(source_element).drag_and_drop(
        source_element, target_element
    ).perform()

    assert driver.raw_tab.sent
    assert source.clicked is True
    assert source.dragged_to == (target, False)


def test_action_chains_move_to_element_with_offset(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15})
    element = WebElement(raw, driver._runner)

    ActionChains(driver).move_to_element_with_offset(element, 5, -3).click().perform()

    assert len(driver.raw_tab.sent) == 3


def test_action_chains_touch_click_at_current_position(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15})
    element = WebElement(raw, driver._runner)

    ActionChains(driver).move_to_element_with_offset(element, 5, -3, input_type="touch").click(input_type="touch").perform()

    assert len(driver.raw_tab.sent) == 2


def test_action_chains_touch_click_alias(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15})
    element = WebElement(raw, driver._runner)

    ActionChains(driver).touch_move_to_element_with_offset(element, 5, -3).touch_click().perform()

    assert len(driver.raw_tab.sent) == 2


def test_action_chains_touch_click_on_element(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15})
    element = WebElement(raw, driver._runner, driver)

    ActionChains(driver).touch_click(element).perform()

    assert len(driver.raw_tab.sent) == 2


def test_action_chains_double_tap(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15})
    element = WebElement(raw, driver._runner)

    ActionChains(driver).double_tap(element).perform()

    assert len(driver.raw_tab.sent) == 4


def test_action_chains_long_press(driver):
    raw = FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15})
    element = WebElement(raw, driver._runner)

    ActionChains(driver).long_press(element, seconds=0).perform()

    assert len(driver.raw_tab.sent) == 2


def test_action_chains_touch_drag(driver):
    source = WebElement(FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15}), driver._runner)
    target = WebElement(FakeElement(rect={"height": 20, "width": 100, "x": 200, "y": 100}), driver._runner)

    ActionChains(driver).touch_drag_and_drop(source, target, steps=3).perform()

    assert len(driver.raw_tab.sent) == 5


def test_action_chains_touch_drag_by_offset(driver):
    source = WebElement(FakeElement(rect={"height": 20, "width": 100, "x": 10, "y": 15}), driver._runner)

    ActionChains(driver).touch_drag_by_offset(source, 30, 40, steps=2).perform()

    assert len(driver.raw_tab.sent) == 4


def test_action_chains_send_keys_to_element(driver):
    raw = FakeElement()
    element = WebElement(raw, driver._runner)

    ActionChains(driver).send_keys_to_element(element, "a", "b").perform()

    assert raw.focused is True
    assert raw.keys == "ab"


def test_keys_constants_match_selenium_values():
    assert Keys.ENTER == "\ue007"
    assert Keys.CONTROL == "\ue009"
    assert Keys.ARROW_LEFT == "\ue012"
    assert Keys.COMMAND == "\ue03d"


def test_element_send_keys_dispatches_special_keys(driver):
    raw = FakeElement()
    element = WebElement(raw, driver._runner, driver)

    element.send_keys("a", Keys.ENTER, "b")

    assert raw.focused is True
    assert raw.keys == "ab"
    assert len(driver.raw_tab.sent) == 2


def test_action_chains_key_down_and_key_up(driver):
    ActionChains(driver).key_down(Keys.CONTROL).key_up(Keys.CONTROL).perform()

    assert len(driver.raw_tab.sent) == 2


def test_action_chains_sends_modified_key_through_cdp(driver):
    ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()

    key_requests = [request for request in driver.raw_tab.cdp_requests if request["method"] == "Input.dispatchKeyEvent"]
    assert len(key_requests) == 4
    assert key_requests[1]["params"]["key"] == "v"
    assert key_requests[1]["params"]["modifiers"] == 2
