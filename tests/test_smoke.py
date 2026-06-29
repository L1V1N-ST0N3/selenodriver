from __future__ import annotations

import os

import pytest

from selenodriver import By, Chrome


@pytest.mark.smoke
@pytest.mark.skipif(os.environ.get("SELENODRIVER_RUN_SMOKE") != "1", reason="set SELENODRIVER_RUN_SMOKE=1 to run real browser smoke tests")
def test_real_browser_data_url_smoke():
    driver = Chrome(headless=True, page_load_timeout=10)
    try:
        driver.get("data:text/html,<button id='x'>OK</button>")
        button = driver.find_element(By.ID, "x")
        assert button.text == "OK"
    finally:
        driver.quit()
