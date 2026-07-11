# selenodriver

Selenium-style synchronous WebDriver API powered by Python `nodriver`.

`selenodriver`는 기존 Selenium 코드 스타일을 최대한 유지하면서, 내부 동작은 `nodriver`와 CDP 기반으로 처리하는 호환 레이어입니다.

## 목차

- [핵심 강점](#핵심-강점)
- [버전과 의존성](#버전과-의존성)
- [빠른 시작](#빠른-시작)
- [클릭과 입력 방식](#클릭과-입력-방식)
- [좌표 클릭 / 랜덤 위치 클릭](#좌표-클릭--랜덤-위치-클릭)
- [모바일 관련 기능](#모바일-관련-기능)
- [현재 구현 범위](#현재-구현-범위)
- [License](#license)
- [개발](#개발)

## 핵심 강점

- Selenium과 비슷한 동기 API: `await` 없이 `driver.get()`, `find_element()`, `element.click()` 형태로 사용합니다.
- CDP 기반 마우스 클릭: 기본 `element.click()`은 JS `el.click()`이 아니라 화면 좌표를 계산해서 `Input.dispatchMouseEvent`를 보냅니다.
- 입력 방식 분리: 마우스 클릭, 터치 클릭, JS 클릭을 명확히 나눠서 사용할 수 있습니다.
- 좌표 기반 제어: element 중앙 클릭뿐 아니라 offset 클릭, 특정 좌표 클릭, element 내부 랜덤 위치 클릭을 지원합니다.
- 모바일 흐름 지원: 터치 클릭, 터치 스크롤, 더블 탭, 롱 프레스, 터치 드래그, 모바일 에뮬레이션 확장을 제공합니다.
- Selenium 호환 import: `selenodriver.webdriver.*` 경로를 지원해 기존 Selenium 코드와 비슷한 구조로 옮기기 쉽습니다.
- 확장 모듈 구조: 외부/private extension을 붙여 브라우저 시작, 이동, 새 탭, context 변경 시점에 자동 로직을 적용할 수 있습니다.

## 버전과 의존성

Current package version:

```text
selenodriver 0.1.1
```

Runtime requirements:

```text
Python >= 3.10
nodriver >= 0.39
```

`nodriver` is declared as a package dependency in `pyproject.toml`, so package installers will install it automatically when installing `selenodriver`.

```toml
dependencies = [
  "nodriver>=0.39",
]
```

## 빠른 시작

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

## 클릭과 입력 방식

`selenodriver`는 클릭 방식을 의도적으로 분리합니다.

| 방식 | 사용 예 | 내부 동작 | 용도 |
| --- | --- | --- | --- |
| 기본/마우스 클릭 | `element.click()` | CDP `Input.dispatchMouseEvent` | 일반 데스크톱 클릭 |
| 명시적 마우스 클릭 | `element.mouse_click()` | CDP `mousePressed` / `mouseReleased` | 기본 클릭과 동일 |
| 터치 클릭 | `element.touch_click()` | CDP `Input.dispatchTouchEvent` | 모바일 탭에 가까운 입력 |
| JS 클릭 | `element.js_click()` | JS `el.click()` | DOM 메서드를 직접 호출해야 할 때 |

기본 클릭은 element의 화면상 중앙 좌표를 기준으로 마우스 이벤트를 보냅니다. JS 클릭이 필요한 경우에는 `js_click()`을 별도로 호출합니다.

## 좌표 클릭 / 랜덤 위치 클릭

Selenium의 `ActionChains` 스타일로 element 중앙이 아닌 지점을 클릭할 수 있습니다.

```python
from selenodriver import ActionChains

ActionChains(driver) \
    .move_to_element_with_offset(element, xoffset, yoffset) \
    .click() \
    .perform()
```

`xoffset`, `yoffset`은 Selenium 호환 기준으로 element의 중앙점 기준입니다.

element 내부의 랜덤 위치를 클릭하려면 좌상단 기준 랜덤 좌표를 만든 뒤 중앙점 기준 offset으로 변환합니다.

```python
import random
from selenodriver import ActionChains

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

같은 위치를 터치 입력으로 누를 수도 있습니다.

```python
ActionChains(driver) \
    .touch_move_to_element_with_offset(element, xoffset, yoffset) \
    .touch_click() \
    .perform()
```

## 모바일 관련 기능

모바일 테스트를 위해 다음 기능을 제공합니다.

- `element.touch_click()`
- `element.click(input_type="touch")`
- `ActionChains(driver).touch_click()`
- `ActionChains(driver).double_tap(element)`
- `ActionChains(driver).long_press(element)`
- `ActionChains(driver).touch_drag_and_drop(source, target)`
- `driver.touch_scroll_by(x, y)`
- `driver.touch_scroll_to(x, y)`
- `element.touch_scroll_into_view()`
- `MobileEmulationExtension("android")`
- `MobileEmulationExtension("ios")`

모바일 에뮬레이션 확장은 UA, viewport, device scale factor, touch emulation, locale, timezone 등을 CDP `Emulation.*` 명령으로 적용합니다. 브라우저 attach, 페이지 이동, context 변경, 새 탭 감지 시점에 다시 적용됩니다.

```python
from selenodriver import Chrome, MobileEmulationExtension

driver = Chrome(
    extensions=[
        MobileEmulationExtension("android")
    ]
)
```

직접 프로필 dict도 사용할 수 있습니다.

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

## 현재 구현 범위

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
- browser helpers: `get`, `back`, `forward`, `refresh`, extension hooks, init scripts, `auto_wait`, `implicitly_wait`, `set_script_timeout`, `timeouts`, `session_id`, `capabilities`, window size/position, legacy find aliases, `find_element`, `find_element_location`, `find_element_absolute_location`, `find_elements`, `execute_script`, `send_cdp`, `execute_cdp_cmd`, `scroll_to`, `scroll_by`, `touch_scroll_by`, `touch_scroll_to`, `page_source`, `title`, `current_url`, `current_window_handle`, `window_handles`, `switch_to.window`, `switch_to.frame`, `switch_to.active_element`, cookies, `save_screenshot`, `close`, `quit`
- action chains: `click`, `touch_click`, `double_click`, `double_tap`, `context_click`, `move_to_element`, `move_to_element_with_offset`, `touch_move_to_element_with_offset`, `move_by_offset`, `drag_and_drop`, `drag_and_drop_by_offset`, `touch_drag_and_drop`, `touch_drag_by_offset`, `click_and_hold`, `long_press`, `release`, `send_keys`, `send_keys_to_element`, `key_down`, `key_up`, `pause`
- expected conditions: `presence_of_element_located`, `visibility_of_element_located`, `element_to_be_clickable`, `invisibility_of_element_located`, `alert_is_present`, `title_is`, `title_contains`, `url_contains`, `url_to_be`, `url_matches`, text checks, and window count checks

더 자세한 사용법은 [한국어 가이드](GUIDE.md)와 [English guide](GUIDE_EN.md)에 정리되어 있습니다.

## License

This project is licensed under the GNU Affero General Public License v3.0.

`selenodriver` depends on `nodriver`, which is licensed under AGPL-3.0, so this project follows the same license family.

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

Run real browser smoke tests explicitly:

```powershell
$env:SELENODRIVER_RUN_SMOKE='1'
pytest -m smoke
```
