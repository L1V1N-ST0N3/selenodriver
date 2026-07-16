import base64
import os

import pytest

from selenodriver import ActionChains, By, Chrome, MobileEmulationExtension


pytestmark = pytest.mark.smoke


def _require_smoke():
    if os.environ.get("SELENODRIVER_RUN_SMOKE") != "1":
        pytest.skip("Set SELENODRIVER_RUN_SMOKE=1 to run real-browser smoke tests")


@pytest.fixture()
def desktop_driver():
    _require_smoke()
    driver = Chrome(headless=True)
    try:
        yield driver
    finally:
        driver.quit()


@pytest.fixture()
def mobile_driver():
    _require_smoke()
    driver = Chrome(headless=True, extensions=[MobileEmulationExtension("android", seed=1)])
    try:
        yield driver
    finally:
        driver.quit()


def test_desktop_navigation_script_and_cdp_input(desktop_driver):
    desktop_driver.get("data:text/html,<input id='field'>")
    field = desktop_driver.find_element(By.ID, "field")

    field.send_keys("abc")

    assert desktop_driver.execute_script("return arguments[0].value", field) == "abc"


def test_execute_async_script_waits_for_completion_callback(desktop_driver):
    result = desktop_driver.execute_async_script(
        "const done = arguments[arguments.length - 1]; "
        "setTimeout(() => done({success: true, id: arguments[0]}), 50);",
        "review-1",
    )

    assert result == {"success": True, "id": "review-1"}


def test_mobile_navigation_script_and_input(mobile_driver):
    mobile_driver.get("data:text/html,<input id='field'>")
    field = mobile_driver.find_element(By.ID, "field")

    field.send_keys("mobile")

    assert mobile_driver.execute_script("return arguments[0].value", field) == "mobile"


@pytest.mark.parametrize(
    ("markup", "attribute"),
    [
        ("<input id='field'>", "value"),
        ("<textarea id='field'></textarea>", "value"),
        ("<div id='field' contenteditable='true'></div>", "textContent"),
    ],
)
def test_desktop_ime_input_targets_editable_elements(desktop_driver, markup, attribute):
    desktop_driver.get("data:text/html;charset=utf-8," + markup)
    field = desktop_driver.find_element(By.ID, "field")

    field.send_keys("한글abc123!@😀", mode="jamo", delay=0.001)

    assert desktop_driver.execute_script(
        f"return arguments[0].{attribute}", field
    ) == "한글abc123!@😀"


def test_action_chains_ime_input(desktop_driver):
    desktop_driver.get("data:text/html;charset=utf-8,<textarea id='field'></textarea>")
    field = desktop_driver.find_element(By.ID, "field")

    ActionChains(desktop_driver).send_keys_to_element(
        field, "가족👨‍👩‍👧‍👦테스트", mode="jamo", delay=0.001
    ).perform()

    assert desktop_driver.execute_script(
        "return arguments[0].value", field
    ) == "가족👨‍👩‍👧‍👦테스트"


def test_mobile_ime_mixed_input(mobile_driver):
    mobile_driver.get("data:text/html;charset=utf-8,<textarea id='field'></textarea>")
    field = mobile_driver.find_element(By.ID, "field")

    field.send_keys("모바일abc123!@😀", mode="jamo", delay=0.001)

    assert mobile_driver.execute_script(
        "return arguments[0].value", field
    ) == "모바일abc123!@😀"


def test_mobile_official_ime_mode(mobile_driver):
    mobile_driver.get("data:text/html;charset=utf-8,<textarea id='field'></textarea>")
    field = mobile_driver.find_element(By.ID, "field")

    field.send_keys("한글English123😀", mode="ime", delay=0.001)

    assert mobile_driver.execute_script(
        "return arguments[0].value", field
    ) == "한글English123😀"


def test_file_input_set_files_dispatches_native_events(desktop_driver, tmp_path):
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    first.write_bytes(b"first-image")
    second.write_bytes(b"second-image")
    desktop_driver.get(
        "data:text/html,<input id='files' type='file' multiple>"
        "<script>window.events=[];const f=document.getElementById('files');"
        "for(const n of ['input','change'])f.addEventListener(n,()=>window.events.push(n));</script>"
    )
    file_input = desktop_driver.find_element(By.ID, "files")

    resolved = file_input.set_files([first, second])

    assert resolved == [str(first.resolve()), str(second.resolve())]
    assert desktop_driver.execute_script(
        "return Array.from(arguments[0].files).map(file => file.name)", file_input
    ) == ["first.jpg", "second.jpg"]
    assert desktop_driver.execute_script("return window.events.join(',')") == "input,change"


def test_clear_uses_native_setter_and_bubbling_events(desktop_driver):
    desktop_driver.get(
        "data:text/html,<textarea id='field'>old review</textarea>"
        "<script>window.events=[];const f=document.getElementById('field');"
        "for(const n of ['input','change'])f.addEventListener(n,()=>window.events.push(n));</script>"
    )
    field = desktop_driver.find_element(By.ID, "field")

    field.clear()

    assert desktop_driver.execute_script("return arguments[0].value", field) == ""
    assert desktop_driver.execute_script("return window.events.join(',')") == "input,change"


def test_mobile_random_touch_click_returns_diagnostics(mobile_driver):
    mobile_driver.get(
        "data:text/html,<button id='target' style='width:160px;height:60px' "
        "onclick=\"this.dataset.clicked='yes'\">Target</button>"
    )
    button = mobile_driver.find_element(By.ID, "target")

    result = button.random_click(input_type="touch", fallback=False)
    snapshot = mobile_driver.capture_diagnostics(element=button)

    assert button.get_attribute("data-clicked") == "yes"
    assert result.method == "touch:random"
    assert snapshot.last_click["method"] == "touch:random"


def test_missing_dom_attribute_returns_none(desktop_driver):
    desktop_driver.get("data:text/html,<button id='expand'>Expand</button>")
    button = desktop_driver.find_element(By.ID, "expand")

    assert button.get_property("ariaExpanded") is None
    assert button.get_attribute("aria-expanded") is None
    assert button.get_dom_attribute("aria-expanded") is None


def test_diagnostic_artifacts_redact_form_values(desktop_driver, tmp_path):
    desktop_driver.get(
        "data:text/html,<input id='input'><textarea id='textarea'></textarea>"
        "<div id='editable' contenteditable='true'></div>"
    )
    desktop_driver.execute_script(
        """
        document.querySelector('#input').value = arguments[0];
        document.querySelector('#textarea').value = arguments[0];
        document.querySelector('#editable').textContent = arguments[0];
        """,
        "private-value",
    )
    screenshot = tmp_path / "failure.png"
    html = tmp_path / "failure.html"

    snapshot = desktop_driver.capture_diagnostics(
        screenshot_path=screenshot,
        html_path=html,
    )

    saved_html = html.read_text(encoding="utf-8")
    assert snapshot.screenshot_path == str(screenshot)
    assert screenshot.stat().st_size > 0
    assert "private-value" not in saved_html
    assert "[REDACTED]" in saved_html


def test_desktop_print_page_and_common_element_metadata(desktop_driver):
    desktop_driver.get("data:text/html,<button id='save' aria-label='Save'>Save</button>")
    button = desktop_driver.find_element(By.ID, "save")

    pdf = base64.b64decode(desktop_driver.print_page({"background": True}))

    assert pdf.startswith(b"%PDF")
    assert desktop_driver.name == "chrome"
    assert button.parent is desktop_driver
    assert button.session_id == desktop_driver.session_id
    assert button.accessible_name == "Save"
    assert button.aria_role in {"button", "Button"}


def test_scrolled_mobile_touch_uses_viewport_coordinates(mobile_driver):
    mobile_driver.get(
        "data:text/html,<body style='height:2400px'>"
        "<button id='target' style='margin-top:1800px;width:120px;height:48px' "
        "onclick=\"this.dataset.clicked='yes'\">Target</button></body>"
    )
    button = mobile_driver.find_element(By.ID, "target")

    ActionChains(mobile_driver).touch_move_to_element_with_offset(
        button, 20, 0
    ).touch_click().perform()

    assert button.get_attribute("data-clicked") == "yes"
    assert "data-clicked" in button.get_attribute("outerHTML")


def test_element_relative_xpath_returns_ancestor(desktop_driver):
    desktop_driver.get(
        "data:text/html,<button id='outer'><span><svg><path id='pen'></path></svg></span></button>"
    )
    path = desktop_driver.find_element(By.ID, "pen")

    ancestor = path.find_element(By.XPATH, "./../../..")

    assert ancestor.get_attribute("id") == "outer"


def test_global_xpath_does_not_require_dom_enable(desktop_driver, monkeypatch):
    desktop_driver.get("data:text/html,<button id='confirm'>Confirm</button>")
    original_send = desktop_driver.raw_tab.send

    async def reject_dom_enable(command, *args, **kwargs):
        if type(command).__name__ == "generator":
            frame = getattr(command, "gi_frame", None)
            if frame is not None and frame.f_code.co_name == "enable":
                raise AssertionError("Global XPath must not call DOM.enable")
        return await original_send(command, *args, **kwargs)

    monkeypatch.setattr(desktop_driver.raw_tab, "send", reject_dom_enable)

    button = desktop_driver.find_element(
        By.XPATH, "//button[normalize-space(text()) = 'Confirm']"
    )

    assert button.get_attribute("id") == "confirm"
