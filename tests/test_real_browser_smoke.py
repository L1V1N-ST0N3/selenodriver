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
