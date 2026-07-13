# selenodriver Guide

`selenodriver` provides a synchronous, Selenium-style API backed by `nodriver` and Chrome DevTools Protocol (CDP).

## Installation

```powershell
python -m pip install selenodriver
```

Version 0.2.0 requires Python 3.10 or newer and installs `nodriver>=0.39` as a runtime dependency.

### Version 0.2.0

Version 0.2.0 promotes randomized touch/mouse clicks, element-relative offsets, viewport-to-screen conversion, privacy-conscious diagnostics, PDF printing, and `mode="ime"` to public APIs. `mode="jamo"` remains an alias. Common Selenium element metadata, expected conditions, wheel scrolling, options, and exception names are also expanded. BiDi, FedCM, virtual-authenticator, and downloadable-files APIs remain out of scope.

### Version 0.1.9

Selenium-compatible `execute_async_script(script, *args)` waits for the completion callback passed as the script's final argument. `set_script_timeout()` controls the maximum wait and a timeout raises `TimeoutException`.

### Version 0.1.8

`ElementNotInteractableException` is now public. With `auto_wait=True`, clicking an element that remains hidden or disabled after the wait raises this exception instead of a generic `TimeoutException`.

```python
from selenodriver import ElementNotInteractableException

try:
    element.click()
except ElementNotInteractableException:
    element = driver.find_element(By.CSS_SELECTOR, "button")
```

### Version 0.1.7

- `ActionChains.move_to_element()` and `move_to_element_with_offset()` bring scrolled targets into view before dispatching input.
- CDP mouse and touch events use viewport coordinates instead of document coordinates.
- `touch_click()` keeps scrolling within its swipe limit until the target enters the viewport.
- `get_attribute()` falls back to DOM properties such as `outerHTML` and `innerText` when no matching HTML attribute exists.
- Touch drag and offset-drag operations use the same viewport coordinate system.

Offsets remain relative to the element center:

```python
ActionChains(driver).touch_move_to_element_with_offset(
    button, 20, 0
).touch_click().perform()

html = button.get_attribute("outerHTML")
```

## Quick Start

```python
from selenodriver import By, Chrome, Options
from selenodriver.support import expected_conditions as EC
from selenodriver.support.ui import WebDriverWait

options = Options()
options.add_argument("--no-first-run")

driver = Chrome(options=options, headless=True)
driver.get("https://example.com")

heading = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.TAG_NAME, "h1"))
)
print(heading.text)
driver.quit()
```

## Options

`Options` and `ChromeOptions` are aliases. Browser arguments, binary location, language, preferences, headless mode, and user profiles are supported.

```python
from selenodriver import Chrome, Options

options = Options()
options.add_arguments("--no-first-run", "--disable-sync")
options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
options.headless = True
options.lang = "en-US"
options.set_user_data_dir("profile")

driver = Chrome(options=options)
```

The Selenium-style user data argument is also recognized and converted to nodriver's dedicated option:

```python
options.add_argument(r"--user-data-dir=C:\profiles\account-1")
```

## Locators

```python
from selenodriver import By

driver.find_element(By.ID, "login")
driver.find_element(By.NAME, "email")
driver.find_element(By.CSS_SELECTOR, ".item")
driver.find_element(By.XPATH, "//main//button")
driver.find_elements(By.TAG_NAME, "a")
```

XPath can be scoped to an existing element:

```python
container = driver.find_element(By.CSS_SELECTOR, ".container")
button = container.find_element(By.XPATH, ".//button")
items = container.find_elements(By.XPATH, ".//li")
parent = button.find_element(By.XPATH, "./..")
ancestor = button.find_element(By.XPATH, "./../..")
```

Parent-only relative XPath expressions such as `./..` and `./../..` traverse nodriver's CDP DOM tree directly, so they can return ancestors outside the element's descendant subtree.

Global XPath uses CDP DOM search commands directly instead of nodriver's `Tab.xpath()`, allowing XPath lookup on older Chrome targets that do not expose `DOM.enable`.

## WebElement

```python
element.click()             # CDP coordinate click
element.mouse_click()       # explicit mouse event
element.touch_click()       # touchStart/touchEnd
element.js_click()          # JavaScript click
result = element.random_click(input_type="touch", fallback=True)
element.send_keys("hello")
element.clear()
element.scroll_into_view()

print(element.text)
print(element.tag_name)
print(element.get_attribute("href"))
print(element.get_property("value"))
print(element.rect)
```

The default click uses viewport coordinates and CDP input events. Use `js_click()` only when JavaScript activation is specifically required.

`random_click()` keeps a safe in-element margin, checks `elementFromPoint()`, and can fall back from a randomized point to center touch, center mouse, and JavaScript. It returns a `ClickResult` containing the method, viewport coordinates, attempted stages, and before/after URLs. Use `driver.click_element_offset(element, x, y)` for top-left-relative offsets or enable randomized plain clicks with `Chrome(randomize_clicks=True)`.

## JavaScript

Both expression style and Selenium's top-level `return` style are supported:

```python
title = driver.execute_script("document.title")
same_title = driver.execute_script("return document.title")
text = driver.execute_script("return arguments[0].textContent", element)
```

Serializable CDP `RemoteObject` values are normalized to Python values. JavaScript exception details raise `SelenoDriverException`.

Since version 0.1.2, scripts with arguments use the CDP `objectId` for `globalThis` as their execution context. Element and global object handles share a per-execution object group that is released after both successful and failed calls. Object resolution and JavaScript execution failures raise `SelenoDriverException`.

Since version 0.1.9, callback-based asynchronous scripts are supported:

```python
driver.set_script_timeout(10)
result = driver.execute_async_script("""
const done = arguments[arguments.length - 1];
fetch(arguments[0])
  .then(response => response.json())
  .then(data => done(data));
""", api_url)
```

The callback's first argument becomes the Python return value. If the callback is not called before the configured script timeout, `TimeoutException` is raised.

Shadow roots support both CSS selectors and XPath:

```python
shadow = host.shadow_root
button = shadow.find_element(By.XPATH, ".//button[@type='submit']")
items = shadow.find_elements(By.XPATH, ".//li")
```

## ActionChains and Keys

```python
from selenodriver import ActionChains, Keys

ActionChains(driver).move_to_element(element).click().perform()
ActionChains(driver).drag_and_drop(source, target).perform()
ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
```

Modifier combinations are sent through CDP key events. This allows combinations such as Ctrl+V to behave as keyboard input instead of appending the literal character with JavaScript.

Plain text from `WebElement.send_keys()` and `ActionChains.send_keys()` is also sent through CDP `Input.dispatchKeyEvent` by default. The same API works for desktop and mobile emulation. Use `send_keys_js()` only when direct JavaScript value mutation is explicitly required.

```python
element.send_keys("abc")       # default: real CDP keyboard input
element.send_keys_js("abc")    # explicit JavaScript value mutation
element.send_keys("한글", mode="auto")  # Korean uses Input.insertText
element.send_keys("한글", mode="ime")   # CDP IME composition events
element.send_keys("abc", delay=0.05)     # delay between events
```

### Input mode details

```python
element.send_keys("hello 한글 😀", mode="auto")
element.send_keys("hello", mode="key")
element.send_keys("한글 😀", mode="text")
element.send_keys("한글", mode="ime", focus=True)

ActionChains(driver).send_keys("한글 😀", mode="auto", delay=0.05).perform()
ActionChains(driver).send_keys_to_element(
    element, "한글", mode="ime", delay=0.05
).perform()
```

`auto` uses CDP key events for ASCII and `Input.insertText` for Hangul and emoji. `key` attempts key events for ASCII/Hangul and uses text insertion for emoji. `text` sends completed text through `Input.insertText`, while `ime` composes and commits Hangul through renderer-scoped CDP `Input.imeSetComposition`.

With `ime`, `focus=True` clicks the element through CDP before input. It does not depend on Windows foreground focus, OS Korean/English state, or `pyautogui`, and uses the same path on other operating systems and mobile emulation. `jamo` remains a compatibility alias for `ime`.

Check the package version:

```python
import selenodriver

print(selenodriver.__version__)
```

Input modes:

- `auto`: uses `Input.insertText` for Hangul/Unicode and key events for other text
- `key`: attempts `keyDown`/`keyUp` for ASCII/Hangul and uses `Input.insertText` for emoji and compound Unicode
- `text`: sends all values through `Input.insertText`
- `ime`: emits and commits CDP IME composition events for Hangul while using key events for ASCII
- `jamo`: compatibility alias for `ime`

`ime` mode is intended for fields that react to real composition events and does not change the operating system input language. Prefer the lighter `auto` mode for simple value input. `ActionChains.send_keys()` and `send_keys_to_element()` support the same mode and `delay` arguments.

Emoji and compound emoji use `Input.insertText` in every mode. ZWJ family emoji, skin-tone modifiers, and variation selectors are grouped as grapheme clusters so the sequence is not split into unrelated key events.

`ime` and `jamo` do not use Windows `SendInput` or `pyautogui`. Legacy helpers under `selenodriver.windows_ime` remain importable for compatibility but are not called by package input modes.

### Failure diagnostics

```python
snapshot = driver.capture_diagnostics(
    element=element,
    error=error,
    screenshot_path="diagnostics/failure.png",
    html_path="diagnostics/failure.html",
)
```

The snapshot contains URL/window state, safe element metadata, the last click method and coordinates, the last input mode and length, and extension errors. It does not record input text or cookies. Requested HTML is cloned and redacted for input values, textareas, and contenteditable fields before it is written.

Mouse, touch, offset clicks, drag operations, long press, key down/up, pauses, and element-focused input are available. This is not a complete W3C Actions implementation.

## Waits

```python
from selenodriver.support import expected_conditions as EC
from selenodriver.support.ui import WebDriverWait

element = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit"))
)
```

Implicit waits are also available through `driver.implicitly_wait(seconds)`. Prefer explicit waits when timing needs to remain predictable.

## Alerts

```python
alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
print(alert.text)
alert.accept()
```

`driver.switch_to.alert` raises `NoAlertPresentException` when no dialog is open. `EC.alert_is_present()` catches that condition and returns `False` while waiting.

## Cookies

```python
driver.add_cookie({"name": "session", "value": "abc"})
cookie = driver.get_cookie("session")
cookies = driver.get_cookies()
driver.delete_cookie("session")
driver.delete_all_cookies()
```

`get_cookies()` first requests cookies for the current URL. If that request fails or returns no cookies, it falls back to all browser cookies. Results are returned as Selenium-style dictionaries.

## Windows and Frames

```python
handles = driver.window_handles
driver.switch_to.window(handles[-1])

driver.switch_to.frame(frame_element)
driver.switch_to.parent_frame()
driver.switch_to.default_content()
```

`close()` closes the current tab. `quit()` closes the browser and the synchronous runner owned by the driver.

## Screenshots and Scrolling

```python
driver.save_screenshot("page.png")
element.screenshot("element.png")

driver.scroll_to(0, 1000)
driver.scroll_by(0, 300)
driver.touch_scroll_by(0, 300)
driver.touch_scroll_to(0, 1000)
```

## Direct CDP

The primary typed API accepts nodriver CDP command generators:

```python
from nodriver import cdp

driver.send_cdp(
    cdp.input_.dispatch_mouse_event("mouseMoved", x=100, y=100)
)
```

Init scripts have dedicated helpers:

```python
script_id = driver.add_init_script("window.__marker = true")
driver.remove_init_script(script_id)
```

For Selenium migration, `execute_cdp_cmd()` provides a thin compatibility wrapper for adding and removing init scripts:

```python
result = driver.execute_cdp_cmd(
    "Page.addScriptToEvaluateOnNewDocument",
    {"source": "window.__marker = true"},
)
driver.execute_cdp_cmd(
    "Page.removeScriptToEvaluateOnNewDocument",
    {"identifier": result["identifier"]},
)
```

Unsupported string-based commands raise `SelenoDriverException`; use `send_cdp()` for other CDP domains.

## Extensions and Mobile Emulation

Extensions can run hooks when the driver attaches, navigates, changes context, discovers a tab, or quits. `MobileEmulationExtension` configures user agent, viewport, device scale factor, touch emulation, locale, and timezone through CDP.

```python
from selenodriver import Chrome, MobileEmulationExtension

driver = Chrome(extensions=[MobileEmulationExtension("android")])
```

## Exceptions

```text
SelenoDriverException
WebDriverException
NoAlertPresentException
NoSuchElementException
NoSuchWindowException
NoSuchFrameException
StaleElementReferenceException
ElementClickInterceptedException
TimeoutException
```

`WebDriverException` is an alias of the base `SelenoDriverException`.

## Compatibility Imports

Selenium-like package paths are available:

```python
from selenodriver.webdriver.chrome.options import Options
from selenodriver.webdriver.common.action_chains import ActionChains
from selenodriver.webdriver.common.by import By
from selenodriver.webdriver.common.keys import Keys
from selenodriver.webdriver.support.ui import WebDriverWait, Select
from selenodriver.webdriver.support import expected_conditions as EC
```

## Development

```powershell
python -m pip install -e .
python -m pip install pytest
pytest
```

The unit suite uses fake nodriver objects. Opt-in real-browser smoke tests require a local Chrome installation:

```powershell
$env:SELENODRIVER_RUN_SMOKE = "1"
pytest -m smoke
```
