import os

import pytest

from selenodriver import By, Chrome, MobileEmulationExtension


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
