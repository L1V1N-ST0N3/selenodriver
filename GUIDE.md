# selenodriver Guide

`selenodriver`는 Python `nodriver` 위에 Selenium 스타일의 동기 API를 제공하는 호환 레이어입니다. 목표는 기존 Selenium 코드의 구조를 최대한 유지하면서 `nodriver` 기반으로 브라우저를 제어하는 것입니다.

## 목차

- [기본 사용](#기본-사용)
- [버전과 의존성](#버전과-의존성)
- [빠른 기능 요약](#빠른-기능-요약)
- [마우스/클릭 강점](#마우스클릭-강점)
- [모바일/터치 강점](#모바일터치-강점)
- [Options](#options)
- [Driver](#driver)
- [Locator](#locator)
- [WebElement](#webelement)
- [Click](#click)
- [ActionChains](#actionchains)
- [Keys](#keys)
- [WebDriverWait](#webdriverwait)
- [Window Handles](#window-handles)
- [Cookies](#cookies)
- [Screenshots](#screenshots)
- [Window Size And Position](#window-size-and-position)
- [Scroll Helpers](#scroll-helpers)
- [Direct CDP](#direct-cdp)
- [Extension Modules](#extension-modules)
- [Mobile Emulation Extension](#mobile-emulation-extension)
- [Frames](#frames)
- [Select](#select)
- [Implicit Wait](#implicit-wait)
- [Exceptions](#exceptions)
- [현재 제한 사항](#현재-제한-사항)
- [개발](#개발)

## 기본 사용

```python
from selenodriver import By, Chrome

driver = Chrome(headless=True)
driver.get("https://example.com")

heading = driver.find_element(By.TAG_NAME, "h1")
print(heading.text)

driver.quit()
```

`nodriver`는 async 기반이지만, `selenodriver`는 내부 이벤트 루프를 관리하므로 일반 Selenium 코드처럼 `await` 없이 사용할 수 있습니다.

Selenium과 비슷한 import 경로도 지원합니다.

```python
from selenodriver.webdriver.common.by import By
from selenodriver.webdriver.common.keys import Keys
from selenodriver.webdriver.common.action_chains import ActionChains
from selenodriver.webdriver.chrome.options import Options
from selenodriver.webdriver.support.ui import WebDriverWait, Select
from selenodriver.webdriver.support import expected_conditions as EC
```

## 버전과 의존성

현재 패키지 버전은 `0.1.3`입니다.

패키지 요구사항:

```text
Python >= 3.10
nodriver >= 0.39
```

`nodriver`는 `pyproject.toml`의 runtime dependency로 들어가 있습니다. 나중에 PyPI나 GitHub 기반으로 패키지를 설치하면 installer가 `nodriver>=0.39`도 같이 설치합니다.

```toml
[project]
version = "0.1.3"
requires-python = ">=3.10"
dependencies = [
  "nodriver>=0.39",
]
```

## 빠른 기능 요약

| 영역 | 지원 기능 | 대표 코드 |
| --- | --- | --- |
| 탐색 | `get`, `back`, `forward`, `refresh` | `driver.get(url)` |
| 요소 찾기 | CSS, XPath, id, name, tag, class | `driver.find_element(By.CSS_SELECTOR, ".login")` |
| 마우스 클릭 | 중앙 클릭, offset 클릭, 랜덤 위치 클릭 | `element.click()` |
| 터치 입력 | 터치 클릭, 더블 탭, 롱 프레스, 터치 드래그 | `element.touch_click()` |
| JS 실행 | Selenium식 `arguments[0]` 지원 | `driver.execute_script("return arguments[0].textContent", element)` |
| Wait | `WebDriverWait`, `EC.*`, optional auto wait | `wait.until(EC.element_to_be_clickable(locator))` |
| 모바일 | Android/iOS 프로필, viewport, UA, touch emulation | `MobileEmulationExtension("android")` |
| CDP | raw CDP 명령 직접 전달 | `driver.send_cdp(command)` |
| 확장 | attach/navigation/new tab/context hook | `driver.use(extension)` |

## 마우스/클릭 강점

`selenodriver`의 기본 클릭은 Selenium 코드 스타일을 유지하지만 내부는 CDP 좌표 이벤트에 가깝게 동작합니다.

- `element.click()`은 JS `el.click()`이 아니라 element 중앙 좌표에 마우스 이벤트를 보냅니다.
- `element.mouse_click()` 또는 `element.click(input_type="mouse")`로 마우스 입력임을 명시할 수 있습니다.
- `ActionChains.move_to_element_with_offset()`으로 element 중앙이 아닌 특정 offset 지점을 클릭할 수 있습니다.
- element의 `size`, `location`, `rect`를 이용해 좌표 기반 로직을 만들 수 있습니다.
- 랜덤 위치 클릭은 element 내부 좌상단 기준 좌표를 만든 뒤 Selenium 호환 offset으로 변환해서 처리합니다.
- JS 클릭은 `element.js_click()`으로 분리되어 있어서 실제 입력 이벤트와 DOM 메서드 호출을 구분할 수 있습니다.

예시:

```python
element.click()                  # 중앙 좌표 마우스 클릭
element.mouse_click()            # 명시적 마우스 클릭
element.js_click()               # JS el.click()

ActionChains(driver) \
    .move_to_element_with_offset(element, 10, -5) \
    .click() \
    .perform()
```

## 모바일/터치 강점

모바일 테스트에서는 화면 크기만 바꾸는 것보다 입력 이벤트까지 터치 기반으로 맞추는 것이 중요합니다.

- `element.touch_click()`은 CDP `Input.dispatchTouchEvent`로 `touchStart` / `touchEnd`를 보냅니다.
- `element.click(input_type="touch")` 또는 `element.click(use_touch=True)`도 지원합니다.
- `ActionChains.touch_click()`, `double_tap()`, `long_press()`, `touch_drag_and_drop()`을 제공합니다.
- `driver.touch_scroll_by()` / `touch_scroll_to()`는 JS scroll이 아니라 터치 swipe 이벤트를 보냅니다.
- `MobileEmulationExtension`은 UA, viewport, DPR, touch emulation, locale, timezone을 CDP로 적용합니다.
- extension hook을 통해 브라우저 attach, 페이지 이동, context 변경, 새 탭 감지 시점에 모바일 설정을 자동 재적용합니다.

예시:

```python
element.touch_click()

ActionChains(driver) \
    .touch_move_to_element_with_offset(element, 12, 8) \
    .touch_click() \
    .perform()

driver.touch_scroll_by(0, 300)
```

## Options

Selenium의 `ChromeOptions`와 비슷하게 브라우저 실행 옵션을 구성할 수 있습니다.

```python
from selenodriver import Chrome, Options

options = Options()
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")
options.add_argument("--disable-background-networking")
options.add_argument("--disable-component-update")
options.add_argument("--disable-default-apps")
options.add_argument("--disable-sync")
options.add_argument("--disable-features=ChromeWhatsNewUI,OptimizationHints,MediaRouter")

driver = Chrome(options=options, headless=True)
```

여러 개를 한 번에 넣을 수도 있습니다.

```python
options.add_arguments(
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
)
```

기타 지원:

```python
options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
options.headless = True
options.set_user_data_dir("profile")
options.lang = "ko-KR"
options.add_experimental_option("prefs", {"download.default_directory": "downloads"})
```

Selenium에서 흔히 사용하는 인자 형식도 지원합니다. 이 값은 nodriver의 전용 `user_data_dir` 옵션으로 분리됩니다.

```python
options.add_argument(r"--user-data-dir=C:\profiles\my-profile")
```

호환 import:

```python
from selenodriver.webdriver.chrome.options import Options
```

내부적으로는 `nodriver.start(browser_args=[...])` 등으로 변환됩니다. `Chrome(options=options, browser_args=[...])`처럼 직접 kwargs를 같이 넘기면 직접 넘긴 kwargs가 우선합니다.

## Driver

### 브라우저 생성

```python
driver = Chrome(headless=True)
```

`Chrome`에 전달한 추가 keyword argument는 내부적으로 `nodriver.start(**kwargs)`에 전달됩니다.

페이지 로딩 대기 전략도 지정할 수 있습니다.

```python
driver = Chrome(page_load_strategy="normal")  # 기본값, document.readyState == "complete"
driver = Chrome(page_load_strategy="eager")   # "interactive" 또는 "complete"
driver = Chrome(page_load_strategy="none")    # get() 후 별도 대기 없음
```

Auto wait는 기본적으로 꺼져 있습니다.

```python
driver = Chrome(auto_wait=True, auto_wait_timeout=10)
driver.set_auto_wait(timeout=10)
driver.disable_auto_wait()
```

`auto_wait=True`일 때:

- `find_element()`는 요소가 나타날 때까지 polling합니다.
- 좌표 기반 `element.click()` / `mouse_click()`은 visible + enabled 상태까지 기다린 뒤 스크롤하고 클릭합니다.
- `element.touch_click()`도 visible + enabled 상태까지 기다린 뒤 터치 입력을 보냅니다.
- `element.send_keys()`는 visible + enabled 상태까지 기다린 뒤 입력합니다.

`element.js_click()`에는 auto wait를 적용하지 않습니다. JS 클릭은 사용자가 의도적으로 DOM 메서드를 직접 호출하는 escape hatch로 둡니다.

페이지 로딩 timeout:

```python
driver.set_page_load_timeout(10)
driver.set_script_timeout(10)
driver.implicitly_wait(5)
print(driver.timeouts.page_load)
print(driver.timeouts.script)
print(driver.timeouts.implicit_wait)
```

### 페이지 이동

```python
driver.get("https://example.com")
driver.back()
driver.forward()
driver.refresh()
```

`get()`, `back()`, `forward()`, `refresh()`는 기본적으로 페이지 로딩 완료까지 기다립니다.

### 페이지 정보

```python
print(driver.title)
print(driver.current_url)
print(driver.page_source)
print(driver.session_id)
print(driver.capabilities)
```

### JavaScript 실행

```python
result = driver.execute_script("document.title")
same_result = driver.execute_script("return document.title")
```

표현식과 Selenium식 top-level `return`을 모두 지원하며 CDP `RemoteObject` 결과는 가능한 경우 Python 값으로 변환합니다.

Selenium식 `arguments[0]` element 전달도 지원합니다.

```python
driver.execute_script("arguments[0].click();", element)
text = driver.execute_script("return arguments[0].textContent;", element)
```

`0.1.2`부터 argument가 있는 script는 `globalThis`의 CDP `objectId`를 실행 context로 사용합니다. element와 global object handle은 실행별 object group으로 관리되어 성공하거나 예외가 발생한 뒤에도 정리됩니다. CDP object 해석 또는 JavaScript 실행이 실패하면 `SelenoDriverException`이 발생합니다.

## Locator

지원하는 `By`:

```python
By.ID
By.XPATH
By.LINK_TEXT
By.PARTIAL_LINK_TEXT
By.NAME
By.TAG_NAME
By.CLASS_NAME
By.CSS_SELECTOR
```

예:

```python
driver.find_element(By.CSS_SELECTOR, "button.swt-close-btn")
driver.find_element(By.XPATH, "//button[contains(@class, 'swt-close-btn')]")
driver.find_element(By.ID, "submit")
driver.find_element(By.NAME, "q")
```

구버전 Selenium alias도 일부 지원합니다.

```python
driver.find_element_by_css_selector(".item")
driver.find_element_by_xpath("//div")
driver.find_element_by_id("submit")
driver.find_element_by_name("q")
driver.find_element_by_tag_name("button")
driver.find_element_by_class_name("active")
```

CSS selector는 그대로 nodriver selector로 전달됩니다.

```python
button_CSS = "button[class='swt-close-btn']"
close_btn = driver.find_element(By.CSS_SELECTOR, button_CSS)
```

다만 class가 여러 개 붙을 수 있는 요소라면 아래 방식이 더 안전합니다.

```python
close_btn = driver.find_element(By.CSS_SELECTOR, "button.swt-close-btn")
```

## WebElement

`find_element()`는 `selenodriver.WebElement`를 반환합니다.

```python
element = driver.find_element(By.CSS_SELECTOR, "button")
```

Element 내부에서도 CSS selector와 XPath로 하위 element를 찾을 수 있습니다.

```python
container = driver.find_element(By.CSS_SELECTOR, ".container")
button = container.find_element(By.XPATH, ".//button")
items = container.find_elements(By.XPATH, ".//li")
```

### 텍스트와 속성

```python
print(element.text)
print(element.tag_name)
print(element.get_attribute("href"))
print(element.get_dom_attribute("href"))
print(element.get_property("checked"))
print(element.value_of_css_property("display"))
```

### 입력

```python
element.clear()
element.send_keys("hello")
element.submit()
element.scroll_into_view()
```

특수키:

```python
from selenodriver import Keys

element.send_keys("hello", Keys.ENTER)
```

### 크기와 위치

Selenium과 같은 형태로 사용할 수 있습니다.

```python
element_size = element.size
element_width = element_size["width"]
element_height = element_size["height"]

print(element.location)  # {"x": ..., "y": ...}
print(element.rect)      # {"x": ..., "y": ..., "width": ..., "height": ...}
```

요소를 찾는 동시에 위치만 바로 받고 싶다면 편의 메서드도 사용할 수 있습니다.

```python
location = driver.find_element_location(By.CSS_SELECTOR, "button")
print(location)  # {"x": ..., "y": ...}
```

이미 찾은 element 객체도 넘길 수 있습니다.

```python
element = driver.find_element(By.CSS_SELECTOR, "button")
location = driver.find_element_location(element)
```

브라우저 창 위치와 추가 보정값까지 더한 좌표가 필요하면 절대 좌표 helper를 사용합니다.

```python
absolute_location = driver.find_element_absolute_location(element)
```

또는 `find_element_location()`에서 옵션으로 받을 수도 있습니다.

```python
absolute_location = driver.find_element_location(
    element,
    absolute=True,
)
```

이 방식은 내부적으로 `driver.get_window_rect()`의 `x`, `y`와 `element.location`을 더합니다.
추가 보정값이 필요하면 반환된 좌표에 직접 더하면 됩니다.

```python
absolute_location["x"] += 10
absolute_location["y"] += 20
```

`size`, `location`, `rect`는 내부적으로 `getBoundingClientRect()`를 사용합니다.

### 스크린샷

```python
element.screenshot("element.png")
png_bytes = element.screenshot_as_png
base64_png = element.screenshot_as_base64
```

### 표시/활성 상태

```python
element.is_displayed()
element.is_enabled()
element.is_selected()
```

`is_enabled()`는 `disabled` 속성과 `aria-disabled="true"`를 확인합니다.

`switch_to.active_element`도 지원합니다.

```python
active = driver.switch_to.active_element
active.send_keys("hello")
```

### Shadow DOM

Shadow root 내부에서도 CSS selector와 XPath를 사용할 수 있습니다.

```python
shadow = host.shadow_root
button = shadow.find_element(By.XPATH, ".//button[@type='submit']")
items = shadow.find_elements(By.XPATH, ".//li")
```

XPath 결과는 shadow root를 context node로 평가하며, 조회 중 임시 marker를 사용한 뒤 정리합니다.

```python
shadow = element.shadow_root
button = shadow.find_element(By.CSS_SELECTOR, "button")
button.click()
```

현재 shadow root는 nodriver raw element가 `shadow_roots` 또는 `shadow_root`를 제공하는 경우를 감싸는 방식입니다. XPath shadow lookup은 아직 구현하지 않았습니다.

## Click

`selenodriver`는 클릭 방식을 명확히 분리합니다.

| 메서드 | 입력 방식 | 좌표 기준 | JS 실행 여부 |
| --- | --- | --- | --- |
| `element.click()` | mouse | element 중앙 | 아니오 |
| `element.mouse_click()` | mouse | element 중앙 | 아니오 |
| `element.click(input_type="touch")` | touch | element 중앙 | 아니오 |
| `element.touch_click()` | touch | element 중앙 | 아니오 |
| `element.js_click()` | JS | 좌표 없음 | 예 |
| `ActionChains(...).move_to_element_with_offset(...).click()` | mouse | element 중앙 + offset | 아니오 |
| `ActionChains(...).touch_move_to_element_with_offset(...).touch_click()` | touch | element 중앙 + offset | 아니오 |

### 기본 클릭

```python
element.click()
```

기본 클릭은 JS `element.click()`이 아닙니다. element의 화면상 중앙 좌표를 계산한 뒤 CDP `Input.dispatchMouseEvent`로 `mousePressed` / `mouseReleased`를 보냅니다.

### 마우스 클릭

```python
element.mouse_click()
element.click(input_type="mouse")
```

기본 `element.click()`과 같습니다.

### 터치 클릭

```python
element.touch_click()
element.click(input_type="touch")
element.click(use_touch=True)
```

element 중앙 좌표에 CDP `Input.dispatchTouchEvent`로 `touchStart` / `touchEnd`를 보냅니다.

### JS 클릭

```python
element.js_click()
element.click(input_type="js")
```

이 방식만 JS `el.click()`을 실행합니다. 좌표 기반 클릭이 아니므로 실제 마우스/터치 입력과는 다릅니다.

## ActionChains

```python
from selenodriver import ActionChains

ActionChains(driver).move_to_element(element).click().perform()
```

modifier 키 조합은 CDP key event로 전달됩니다.

```python
from selenodriver import Keys

ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
```

`WebElement.send_keys()`와 `ActionChains.send_keys()`의 일반 문자열은 기본적으로 CDP `Input.dispatchKeyEvent`로 전달됩니다. 따라서 실제 keydown/keyup 및 input 흐름을 사용하며 PC와 모바일 emulation에서 같은 API를 사용할 수 있습니다. JavaScript로 value를 직접 변경해야 하는 경우에만 명시적으로 `send_keys_js()`를 사용합니다.

```python
element.send_keys("abc")       # 기본값: 실제 CDP 키 입력
element.send_keys_js("abc")    # 명시적 JS value 변경
```

액션은 체인에 쌓이고, `perform()` 호출 시 순서대로 실행됩니다.

지원 메서드:

```python
click()
touch_click()
double_click()
double_tap()
context_click()
move_to_element()
move_to_element_with_offset()
touch_move_to_element_with_offset()
move_by_offset()
drag_and_drop()
drag_and_drop_by_offset()
touch_drag_and_drop()
touch_drag_by_offset()
click_and_hold()
long_press()
release()
send_keys()
send_keys_to_element()
key_down()
key_up()
pause()
reset_actions()
perform()
```

### Offset 클릭

Offset 클릭은 element 중앙이 아닌 지점을 누르고 싶을 때 사용합니다. 예를 들어 버튼 중앙이 아니라 오른쪽 안쪽 영역, 체크박스 라벨의 특정 위치, 또는 테스트마다 조금 다른 위치를 누르는 흐름을 만들 수 있습니다.

```python
ActionChains(driver) \
    .move_to_element_with_offset(element, xoffset, yoffset) \
    .click() \
    .perform()
```

Selenium 호환 기준으로 `xoffset`, `yoffset`은 element의 중앙점 기준입니다.

예를 들어 `xoffset=10`, `yoffset=-5`는 element 중앙에서 오른쪽으로 10px, 위로 5px 이동한 지점을 뜻합니다.

요소 내부의 좌상단 기준 랜덤 좌표를 클릭하고 싶다면:

```python
import random

size = element.size
rx = random.randint(5, int(size["width"]) - 5)
ry = random.randint(5, int(size["height"]) - 5)

xoffset = rx - size["width"] / 2
yoffset = ry - size["height"] / 2

ActionChains(driver) \
    .move_to_element_with_offset(element, xoffset, yoffset) \
    .click() \
    .perform()
```

터치 입력으로 같은 위치를 누르려면:

```python
ActionChains(driver) \
    .move_to_element_with_offset(element, xoffset, yoffset, input_type="touch") \
    .click(input_type="touch") \
    .perform()
```

또는:

```python
ActionChains(driver) \
    .touch_move_to_element_with_offset(element, xoffset, yoffset) \
    .touch_click() \
    .perform()
```

터치 offset 이동은 mouseMoved 이벤트를 보내지 않고 좌표만 저장합니다. 그래서 위 흐름은 `touchStart` / `touchEnd`만 발생합니다.

터치 제스처:

```python
ActionChains(driver).double_tap(element).perform()
ActionChains(driver).long_press(element, seconds=0.5).perform()
ActionChains(driver).touch_drag_and_drop(source, target).perform()
ActionChains(driver).touch_drag_by_offset(source, 100, 0).perform()
```

주의: `ActionChains.click()`은 `WebElement.click()`과 다른 메서드입니다. `ActionChains.click()`은 현재 액션 좌표에서 클릭하고, `WebElement.click()`은 해당 element 중앙을 클릭합니다.

## Keys

```python
from selenodriver import Keys

element.send_keys("hello", Keys.ENTER)

ActionChains(driver) \
    .key_down(Keys.CONTROL) \
    .send_keys("a") \
    .key_up(Keys.CONTROL) \
    .perform()
```

주요 지원 키:

```python
Keys.ENTER
Keys.TAB
Keys.ESCAPE
Keys.BACKSPACE
Keys.DELETE
Keys.SHIFT
Keys.CONTROL
Keys.ALT
Keys.COMMAND
Keys.ARROW_LEFT
Keys.ARROW_RIGHT
Keys.ARROW_UP
Keys.ARROW_DOWN
Keys.HOME
Keys.END
Keys.PAGE_UP
Keys.PAGE_DOWN
Keys.F1 ... Keys.F12
```

상수값은 Selenium의 private-use unicode 값과 맞췄습니다.

## WebDriverWait

Selenium식 명시적 대기를 지원합니다.

```python
from selenodriver.support.ui import WebDriverWait
from selenodriver.support import expected_conditions as EC

wait = WebDriverWait(driver, 10)

button = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.swt-close-btn"))
)

button.click()
```

직접 import도 가능합니다.

```python
from selenodriver import WebDriverWait
from selenodriver import expected_conditions as EC
```

`WebDriverWait`는 기본적으로 `NoSuchElementException`을 무시하고 polling합니다.

```python
WebDriverWait(driver, timeout=10, poll_frequency=0.2)
```

### 지원 Expected Conditions

```python
EC.presence_of_element_located(locator)
EC.presence_of_all_elements_located(locator)
EC.visibility_of_element_located(locator)
EC.visibility_of(element)
EC.visibility_of_any_elements_located(locator)
EC.visibility_of_all_elements_located(locator)
EC.invisibility_of_element_located(locator)
EC.invisibility_of_element(element)
EC.element_to_be_clickable(locator_or_element)
EC.text_to_be_present_in_element(locator, text)
EC.text_to_be_present_in_element_attribute(locator, attribute, text)
EC.text_to_be_present_in_element_value(locator, text)
EC.title_is(title)
EC.title_contains(title)
EC.url_contains(url)
EC.url_to_be(url)
EC.url_matches(pattern)
EC.number_of_windows_to_be(count)
EC.new_window_is_opened(current_handles)
EC.alert_is_present()
EC.staleness_of(element)
```

### Alert

```python
alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
print(alert.text)
alert.accept()
```

Prompt 입력:

```python
alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
alert.send_keys("hello")
alert.accept()
```

`driver.switch_to.alert`도 사용할 수 있습니다.

```python
alert = driver.switch_to.alert
alert.dismiss()
```

열린 alert가 없으면 `NoAlertPresentException`이 발생합니다. `EC.alert_is_present()`는 이 경우 예외 대신 `False`를 반환합니다.

## Window Handles

```python
handles = driver.window_handles
current = driver.current_window_handle

driver.switch_to.window(handles[1])
driver.close()
driver.quit()
```

`window_handles`를 읽을 때 내부적으로 `browser.update_targets()`를 호출합니다. nodriver는 새 탭/창이 열린 뒤 `browser.tabs` 목록이 자동으로 최신화되지 않을 수 있기 때문입니다.

동작:

```python
handles_before = driver.window_handles

# 새 탭/창이 열리는 클릭
button.click()

handles_after = driver.window_handles  # update_targets() 후 최신 목록 반환
```

`close()`와 `quit()`의 의미는 Selenium에 맞췄습니다.

```python
driver.close()  # 현재 탭 닫기
driver.quit()   # 브라우저 전체 종료
```

## Cookies

```python
driver.add_cookie({"name": "session", "value": "abc"})
driver.get_cookie("session")
driver.get_cookies()
driver.delete_cookie("session")
driver.delete_all_cookies()
```

`get_cookies()`는 현재 URL 범위를 먼저 조회하고 결과가 없거나 실패하면 브라우저 전체 쿠키 조회로 fallback합니다.

쿠키 dict는 Selenium의 일반 형식에 맞췄습니다.

```python
{
    "name": "session",
    "value": "abc",
    "domain": "example.com",
    "path": "/",
    "secure": True,
    "httpOnly": True,
    "expiry": 1893456000,
    "sameSite": "Lax",
}
```

## Screenshots

```python
driver.save_screenshot("page.png")
driver.get_screenshot_as_file("page.png")
png_bytes = driver.get_screenshot_as_png()
base64_png = driver.get_screenshot_as_base64()
```

## Window Size And Position

```python
driver.get_window_size()
driver.set_window_size(1280, 720)

driver.get_window_position()
driver.set_window_position(100, 100)

driver.get_window_rect()
driver.set_window_rect(x=100, y=100, width=1280, height=720)

driver.maximize_window()
driver.minimize_window()
driver.fullscreen_window()
```

## Scroll Helpers

```python
driver.scroll_to(0, 500)
driver.scroll_by(0, 300)
```

위 두 메서드는 JS `window.scrollTo` / `window.scrollBy` 기반입니다.

모바일 입력에 가까운 터치 스크롤도 지원합니다.

```python
driver.touch_scroll_by(0, 300)
driver.touch_scroll_to(0, 1000)
element.touch_scroll_into_view()
```

`touch_scroll_by(x, y)`는 CDP `Input.dispatchTouchEvent`로 `touchStart` / `touchMove` / `touchEnd`를 보냅니다. 손가락 이동은 페이지 스크롤 방향과 반대라서, 내부적으로 `y=300`은 손가락을 위로 움직이는 swipe로 처리됩니다.

## Direct CDP

nodriver CDP command를 직접 보낼 수 있습니다.

```python
from nodriver import cdp

driver.send_cdp(
    cdp.input_.dispatch_mouse_event(
        "mouseMoved",
        x=100,
        y=100,
    )
)
```

element에서도 현재 driver/tab을 통해 CDP command를 보낼 수 있습니다.

```python
element.send_cdp(cdp.dom.scroll_into_view_if_needed(...))
```

Selenium 이식 코드를 위한 얇은 호환 래퍼도 제공합니다. 현재 init script 추가와 제거를 지원하며, 나머지 명령은 타입이 명확한 `send_cdp()` 사용을 권장합니다.

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

더 낮은 수준의 접근이 필요하면 raw 객체도 열어두었습니다.

```python
driver.raw_browser
driver.raw_tab
element.raw
```

## Extension Modules

`selenodriver` 본체 밖의 비공개 모듈을 driver에 붙일 수 있습니다.

```python
from selenodriver import Chrome
from private_mobile_profile import MobileProfileExtension

extension = MobileProfileExtension(profile="android")
driver = Chrome(extensions=[extension])
```

실행 중에도 붙일 수 있습니다.

```python
driver.use(extension)
driver.remove_extension(extension)
```

extension 객체는 필요한 hook만 구현하면 됩니다.

```python
class MyExtension:
    def on_attach(self, driver):
        driver.add_init_script("window.__my_marker = true")

    def before_navigate(self, driver, url):
        pass

    def after_navigate(self, driver, url):
        pass

    def on_context_changed(self, driver):
        pass

    def before_quit(self, driver):
        pass
```

지원 hook:

```python
on_attach(driver)
before_navigate(driver, url)
after_navigate(driver, url)
on_context_changed(driver)
before_quit(driver)
```

초기 문서 스크립트 주입도 제공합니다.

```python
script_id = driver.add_init_script("window.__x = 1", run_immediately=True)
driver.remove_init_script(script_id)
driver.clear_init_scripts()
```

`add_init_script()`는 CDP `Page.addScriptToEvaluateOnNewDocument`를 사용합니다. 비공개 모듈은 이 hook과 `driver.send_cdp(...)`를 조합해서 자기 책임 범위의 프로필 적용 로직을 구성하면 됩니다.

## Mobile Emulation Extension

모바일 장비 없이 모바일 레이아웃/터치/UA 기반 동작을 테스트하기 위한 기본 확장입니다.

```python
from selenodriver import Chrome, MobileEmulationExtension

driver = Chrome(
    extensions=[
        MobileEmulationExtension("android")
    ]
)
```

iOS 기본 프로필:

```python
driver = Chrome(extensions=[MobileEmulationExtension("ios")])
```

기본 프로필 중 랜덤 선택을 고정하려면 seed를 넘깁니다.

```python
extension = MobileEmulationExtension("android", seed=1)
```

직접 프로필을 줄 수도 있습니다.

```python
from selenodriver import MobileEmulationExtension, MobileProfile

profile = MobileProfile(
    name="Internal Test Phone",
    user_agent="Mozilla/5.0 ... Mobile Safari/537.36",
    platform="Android",
    width=390,
    height=844,
    device_scale_factor=3,
    max_touch_points=5,
    locale="ko-KR",
    timezone_id="Asia/Seoul",
)

driver = Chrome(extensions=[MobileEmulationExtension(profile)])
```

dict 입력도 지원합니다.

```python
profile = {
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

driver = Chrome(extensions=[MobileEmulationExtension(profile)])
```

지원 alias:

```python
device_name -> name
UA -> user_agent
devicePixelRatio -> device_scale_factor
language -> locale
languages -> Accept-Language
```

자동 적용 시점:

- driver에 extension attach 시점
- `driver.get(url)` 이전/이후
- `refresh()` 전후
- `switch_to.window(...)`
- `switch_to.frame(...)`
- `default_content()` / `parent_frame()`
- 새 탭이 `update_targets()`로 감지되는 시점

내부적으로 사용하는 CDP:

- `Emulation.setUserAgentOverride`
- `Emulation.setDeviceMetricsOverride`
- `Emulation.setTouchEmulationEnabled`
- `Emulation.setLocaleOverride`
- `Emulation.setTimezoneOverride`

이 확장은 모바일 호환성 테스트용입니다. 프로젝트 고유의 추가 스크립트나 서버별 설정은 별도 비공개 extension에서 `driver.add_init_script(...)` / `driver.send_cdp(...)`를 사용해 붙이는 구조를 권장합니다.

## Frames

```python
driver.switch_to.frame(0)
driver.switch_to.parent_frame()
driver.switch_to.default_content()
```

`switch_to.frame()`은 frame index, frame-like nodriver 객체, 일부 frame element 참조를 지원합니다. nodriver의 frame 연결 가능 여부에 따라 iframe 지원 범위가 달라질 수 있습니다.

## Select

```python
from selenodriver.support.select import Select

select = Select(driver.find_element(By.TAG_NAME, "select"))
select.select_by_value("kr")
select.select_by_visible_text("Korea")
select.select_by_index(0)
```

multi-select에서는 deselect도 지원합니다.

```python
select.deselect_all()
select.deselect_by_value("kr")
select.deselect_by_visible_text("Korea")
select.deselect_by_index(0)
```

## Implicit Wait

```python
driver.implicitly_wait(5)
```

이후 `find_element()`와 `find_elements()`는 지정 시간 동안 polling합니다. 명시적 wait와 섞어 쓰면 대기 시간이 예상보다 길어질 수 있으므로, 가능하면 `WebDriverWait`를 우선 사용하는 편이 명확합니다.

## Exceptions

지원 예외:

```python
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

## 현재 제한 사항

- 완전한 Selenium 대체는 아직 아닙니다.
- `ActionChains`는 기본적인 mouse/touch/key 동작 위주입니다. Selenium의 모든 W3C action sequence를 그대로 구현한 것은 아닙니다.
- 기본 테스트는 fake nodriver 객체 기반 단위 테스트이며, 실제 브라우저 smoke test는 환경 변수로 명시적으로 실행합니다.

## 개발

Install from PyPI:

```powershell
python -m pip install selenodriver
```

For local development and tests:

```powershell
python -m pip install -e .
python -m pip install pytest
pytest
```

실제 브라우저 smoke test는 명시적으로 실행합니다.

```powershell
$env:SELENODRIVER_RUN_SMOKE='1'
pytest -m smoke
```

현재 기본 테스트:

```text
77 passed, 1 skipped
```
