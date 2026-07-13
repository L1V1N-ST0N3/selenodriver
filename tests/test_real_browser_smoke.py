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
