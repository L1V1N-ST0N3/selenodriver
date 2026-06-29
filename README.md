# selenodriver

Selenium-style synchronous WebDriver API powered by Python `nodriver`.

```python
from selenodriver import ActionChains, By, Chrome, Keys, Options
from selenodriver.support import expected_conditions as EC
from selenodriver.support.ui import WebDriverWait

options = Options()
options.add_argument("--no-first-run")
driver = Chrome(headless=True, options=options)
driver.get("https://example.com")

heading = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.TAG_NAME, "h1"))
)
print(heading.text)

ActionChains(driver).move_to_element(heading).click().send_keys(Keys.ENTER).perform()

driver.quit()
```

## Current scope

This is an early compatibility layer, not a full Selenium replacement yet.

Implemented:

- `Chrome`
- `By`
- `WebElement`
- `NoSuchElementException`
- `WebDriverWait`
- `ActionChains`
- `Keys`
- `Select`
- `Options` / `ChromeOptions`
- `MobileEmulationExtension`
- extension hooks for external/private modules
- Selenium-like import paths under `selenodriver.webdriver.*`
- common expected conditions
- locators: CSS selector, XPath, id, name, tag name, class name
- element actions/properties: `click`, `mouse_click`, `touch_click`, `js_click`, `submit`, `scroll_into_view`, `shadow_root`, `send_keys`, `clear`, `text`, `tag_name`, `get_attribute`, `get_dom_attribute`, `get_property`, `value_of_css_property`, `is_selected`, `size`, `location`, `rect`
- browser helpers: `get`, `back`, `forward`, `refresh`, extension hooks, init scripts, `auto_wait`, `implicitly_wait`, `set_script_timeout`, `timeouts`, `session_id`, `capabilities`, window size/position, legacy find aliases, `find_element`, `find_elements`, `execute_script`, `send_cdp`, `scroll_to`, `scroll_by`, `touch_scroll_by`, `touch_scroll_to`, `page_source`, `title`, `current_url`, `current_window_handle`, `window_handles`, `switch_to.window`, `switch_to.frame`, `switch_to.active_element`, cookies, `save_screenshot`, `close`, `quit`
- action chains: `click`, `touch_click`, `double_click`, `double_tap`, `context_click`, `move_to_element`, `move_to_element_with_offset`, `touch_move_to_element_with_offset`, `move_by_offset`, `drag_and_drop`, `drag_and_drop_by_offset`, `touch_drag_and_drop`, `touch_drag_by_offset`, `click_and_hold`, `long_press`, `release`, `send_keys`, `send_keys_to_element`, `key_down`, `key_up`, `pause`
- expected conditions: `presence_of_element_located`, `visibility_of_element_located`, `element_to_be_clickable`, `invisibility_of_element_located`, `alert_is_present`, `title_is`, `title_contains`, `url_contains`, `url_to_be`, `url_matches`, text checks, and window count checks

## Development

Detailed usage notes are in [GUIDE.md](GUIDE.md).

```powershell
python -m pip install -e ".[test]"
pytest
```

Run real browser smoke tests explicitly:

```powershell
$env:SELENODRIVER_RUN_SMOKE='1'
pytest -m smoke
```
