# selenodriver

Selenium-style synchronous WebDriver API powered by Python `nodriver`.

`selenodriver`는 기존 Selenium 코드 스타일을 최대한 유지하면서, 내부 동작은 `nodriver`와 CDP 기반으로 처리하는 호환 레이어입니다.

`selenodriver` is a compatibility layer that preserves familiar Selenium coding patterns while using `nodriver` and CDP internally.

**문서 / Documentation:** [한국어 가이드](https://github.com/L1V1N-ST0N3/selenodriver/blob/master/GUIDE.md) | [English guide](https://github.com/L1V1N-ST0N3/selenodriver/blob/master/GUIDE_EN.md)

## 목차 / Contents

- [핵심 강점 / Key Features](#핵심-강점--key-features)
- [버전과 의존성 / Version and Dependencies](#버전과-의존성--version-and-dependencies)
- [0.1.1 업데이트 내역 / Release Notes](#011-업데이트-내역--release-notes)
- [0.1.2 업데이트 내역 / Release Notes](#012-업데이트-내역--release-notes)
- [0.1.3 업데이트 내역 / Release Notes](#013-업데이트-내역--release-notes)
- [0.1.4 업데이트 내역 / Release Notes](#014-업데이트-내역--release-notes)
- [0.1.5 업데이트 내역 / Release Notes](#015-업데이트-내역--release-notes)
- [0.1.6 업데이트 내역 / Release Notes](#016-업데이트-내역--release-notes)
- [0.1.7 업데이트 내역 / Release Notes](#017-업데이트-내역--release-notes)
- [0.1.8 업데이트 내역 / Release Notes](#018-업데이트-내역--release-notes)
- [빠른 시작 / Quick Start](#빠른-시작--quick-start)
- [클릭과 입력 방식 / Click and Input Modes](#클릭과-입력-방식--click-and-input-modes)
- [좌표 클릭 / Offset and Randomized Clicks](#좌표-클릭--랜덤-위치-클릭--offset-and-randomized-clicks)
- [모바일 관련 기능 / Mobile Features](#모바일-관련-기능--mobile-features)
- [현재 구현 범위 / Implementation Status](#현재-구현-범위--implementation-status)
- [License](#license)
- [개발](#개발)

## 핵심 강점 / Key Features

- Selenium과 비슷한 동기 API: `await` 없이 `driver.get()`, `find_element()`, `element.click()` 형태로 사용합니다.
- CDP 기반 마우스 클릭: 기본 `element.click()`은 JS `el.click()`이 아니라 화면 좌표를 계산해서 `Input.dispatchMouseEvent`를 보냅니다.
- 입력 방식 분리: 마우스 클릭, 터치 클릭, JS 클릭을 명확히 나눠서 사용할 수 있습니다.
- 좌표 기반 제어: element 중앙 클릭뿐 아니라 offset 클릭, 특정 좌표 클릭, element 내부 랜덤 위치 클릭을 지원합니다.
- 모바일 흐름 지원: 터치 클릭, 터치 스크롤, 더블 탭, 롱 프레스, 터치 드래그, 모바일 에뮬레이션 확장을 제공합니다.
- Selenium 호환 import: `selenodriver.webdriver.*` 경로를 지원해 기존 Selenium 코드와 비슷한 구조로 옮기기 쉽습니다.
- 확장 모듈 구조: 외부/private extension을 붙여 브라우저 시작, 이동, 새 탭, context 변경 시점에 자동 로직을 적용할 수 있습니다.

English summary:

- Synchronous Selenium-style API: use `driver.get()`, `find_element()`, and `element.click()` without `await`.
- CDP mouse input: the default click calculates viewport coordinates and dispatches `Input.dispatchMouseEvent` instead of calling JavaScript `el.click()`.
- Explicit input modes: mouse, touch, and JavaScript clicks are separate operations.
- Coordinate control: center, offset, absolute, and randomized in-element clicks are supported.
- Mobile workflows: touch clicks, scrolling, double tap, long press, touch drag, and mobile emulation are included.
- Migration-friendly imports: Selenium-like modules are available under `selenodriver.webdriver.*`.
- Extension hooks: external or private modules can react to browser attach, navigation, tab discovery, and context changes.

## 버전과 의존성 / Version and Dependencies

현재 패키지 버전 / Current package version:

```text
selenodriver 0.1.8
```

The version is also available from Python:

```python
import selenodriver

print(selenodriver.__version__)
```

실행 요구사항 / Runtime requirements:

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

## 0.1.1 업데이트 내역 / Release Notes

`0.1.1`은 실사용 중 확인된 Selenium 호환 문제와 브라우저 상태 처리 문제를 보완한 릴리스입니다.

Version `0.1.1` improves Selenium compatibility and fixes browser-state issues found in real-world usage.

- **JavaScript 실행 / JavaScript execution:** `execute_script()`가 표현식과 Selenium식 top-level `return`을 모두 지원하며, CDP `RemoteObject`를 가능한 경우 Python 값으로 변환합니다. JavaScript 예외 정보는 `SelenoDriverException`으로 전달됩니다. / Supports both expressions and Selenium-style top-level `return`, normalizes CDP `RemoteObject` values, and raises `SelenoDriverException` for JavaScript exception details.
- **쿠키 조회 / Cookie retrieval:** 현재 URL의 쿠키 조회가 실패하거나 빈 결과를 반환하면 브라우저 전체 쿠키 조회로 fallback합니다. / Falls back to browser-wide cookies when the current-URL lookup fails or returns no results.
- **사용자 프로필 / User profiles:** `Options.add_argument("--user-data-dir=...")` 형식을 nodriver의 전용 `user_data_dir` 옵션으로 변환합니다. / Converts Selenium-style `--user-data-dir=...` arguments to nodriver's dedicated `user_data_dir` option.
- **Alert 호환 / Alert compatibility:** alert가 없을 때 `NoAlertPresentException`을 발생시키며, `EC.alert_is_present()`는 대기 중 `False`를 반환합니다. / Raises `NoAlertPresentException` when no alert is open while `EC.alert_is_present()` safely returns `False`.
- **CDP 호환 / CDP compatibility:** Selenium 이식 코드를 위한 `execute_cdp_cmd()` 래퍼를 추가했습니다. init script 추가와 제거를 지원하며, 기존 typed `send_cdp()` API도 그대로 유지됩니다. / Adds an `execute_cdp_cmd()` migration wrapper for adding and removing init scripts while retaining the typed `send_cdp()` API.
- **키 조합 / Key combinations:** `ActionChains`가 modifier 상태를 CDP key event에 전달하여 Ctrl+V 같은 조합을 실제 키 입력으로 처리합니다. / Passes modifier state through CDP key events so combinations such as Ctrl+V behave as real keyboard input.
- **페이지 로드 / Page loading:** `document.readyState` 결과 타입을 방어적으로 처리하여 CDP 객체 때문에 페이지 로드 대기가 실패하지 않도록 했습니다. / Defensively handles `document.readyState` result types to prevent CDP objects from breaking page-load waits.
- **중첩 XPath / Scoped XPath:** `WebElement.find_element(s)(By.XPATH, ...)`를 추가하여 현재 element 기준 XPath 조회를 지원합니다. / Adds element-scoped XPath lookup through `WebElement.find_element(s)(By.XPATH, ...)`.
- **문서 / Documentation:** 한국어 가이드를 갱신하고 별도의 영문 가이드를 추가했습니다. / Updates the Korean guide and adds a dedicated English guide.

## 0.1.2 업데이트 내역 / Release Notes

- **`execute_script(script, *args)` 수정:** `Runtime.callFunctionOn` 호출 시 `globalThis`의 `objectId`를 넘겨 `Either objectId or executionContextId must be specified` 오류를 제거했습니다. / Provides the `globalThis` `objectId` to `Runtime.callFunctionOn`, resolving the missing objectId/context protocol error when script arguments are used.
- **CDP object 수명 관리 / CDP object lifecycle:** script 실행마다 전용 object group을 사용하고 성공·실패 여부와 관계없이 해제하여 remote object handle 누적을 방지합니다. / Uses and always releases a per-execution object group to prevent remote object handles from accumulating.
- **오류 전달 / Error propagation:** element 및 global object 해석 실패와 JavaScript 실행 오류를 `SelenoDriverException`으로 명확히 전달합니다. / Converts element/global object resolution failures and JavaScript execution errors into clear `SelenoDriverException` failures.

## 0.1.3 업데이트 내역 / Release Notes

- **기본 키 입력 / Default keyboard input:** `WebElement.send_keys()`와 `ActionChains.send_keys()`의 일반 문자열이 JavaScript value 조작이 아닌 CDP `Input.dispatchKeyEvent`로 전달됩니다. / Plain text now uses CDP keyboard events instead of JavaScript value mutation.
- **명시적 JS 입력 / Explicit JavaScript input:** JavaScript 방식이 필요한 경우 `WebElement.send_keys_js()`를 사용할 수 있습니다. / `WebElement.send_keys_js()` is available when direct JavaScript value mutation is required.
- **입력 mode와 delay / Input modes and delay:** `auto`, `key`, `text`, `jamo` mode와 문자 사이 `delay` 옵션을 제공합니다. / Adds `auto`, `key`, `text`, and `jamo` modes plus configurable inter-character delay.
- **한글 입력 / Hangul input:** 외부 `jamo` 패키지 없이 Unicode 음절 분해와 두벌식 변환을 지원합니다. / Supports Unicode Hangul decomposition and 2-beolsik conversion without importing the external `jamo` package.
- **이모지 입력 / Emoji input:** 모든 입력 mode에서 emoji와 ZWJ/variation-selector 기반 복합 emoji를 grapheme 단위 `Input.insertText`로 처리합니다. / Handles emoji and ZWJ/variation-selector emoji sequences as grapheme-based `Input.insertText` in every mode.
- **모바일·PC 공통 입력 / Shared desktop and mobile input:** 기본 입력 API가 desktop과 mobile emulation에서 같은 CDP 경로를 사용합니다. / The default input API uses the same CDP path for desktop and mobile emulation.
- **Shadow DOM XPath:** `ShadowRoot.find_element(s)(By.XPATH, ...)`를 지원합니다. / Adds XPath lookup inside shadow roots.
- **CDP wrapper 확장 / CDP wrapper expansion:** Network UA/header와 Emulation 명령을 `execute_cdp_cmd()`에서 지원합니다. / Adds common Network and Emulation commands to `execute_cdp_cmd()`.
- **쿠키 fallback 개선 / Cookie fallback:** deprecated Network 전체 쿠키 명령 대신 Storage domain fallback을 사용합니다. / Uses the Storage domain for the browser-wide cookie fallback.
- **테스트·CI / Tests and CI:** 실제 브라우저 smoke test, Python matrix CI, 공개 `__version__`을 추가했습니다. / Adds opt-in browser smoke tests, Python matrix CI, and a public `__version__`.

## 0.1.4 업데이트 내역 / Release Notes

- **CDP IME 조합 입력 / CDP IME composition:** `jamo` mode가 전역 Windows `SendInput` 대신 포커스된 renderer의 `Input.imeSetComposition`을 사용합니다. 한글 composition 이벤트를 발생시키면서 OS 한/영 상태와 전면 창에 의존하지 않습니다. / `jamo` mode now targets the focused renderer with `Input.imeSetComposition` instead of global Windows `SendInput`, producing Hangul composition events without depending on OS input state or foreground-window focus.
- **혼합 문자열 / Mixed text:** 한글, 영문, 숫자, 특수문자, emoji 및 ZWJ 복합 emoji가 입력 순서대로 처리됩니다. / Hangul, Latin text, numbers, punctuation, emoji, and ZWJ emoji sequences retain their input order.
- **문장부호 키 수정 / Punctuation fix:** `!`와 `#` 등이 PageUp/End Windows virtual key로 오인되던 문제를 수정했습니다. / Fixes punctuation such as `!` and `#` being misinterpreted as PageUp or End virtual keys.
- **PC·모바일 공통 / Desktop and mobile:** 동일한 renderer-scoped 입력 경로를 데스크톱과 모바일 emulation에서 사용합니다. / Uses the same renderer-scoped input path on desktop and mobile emulation.
- **호환성 / Compatibility:** `windows_ime` helper는 0.1.x 호환을 위해 남겨 두지만 패키지 입력 mode에서는 더 이상 사용하지 않습니다. / Legacy `windows_ime` helpers remain importable for 0.1.x compatibility but are no longer used by package input modes.
- **검증 / Verification:** input, textarea, contenteditable, ActionChains 및 모바일용 실제 Chrome smoke coverage를 추가했습니다. / Adds real-Chrome smoke coverage for input, textarea, contenteditable, ActionChains, and mobile emulation.

```python
field.send_keys("한글abc123!@😀", mode="jamo", delay=0.03)
field.send_keys(Keys.ENTER)
```

## 0.1.5 업데이트 내역 / Release Notes

- **상대 부모 XPath / Relative parent XPath:** `element.find_element(By.XPATH, "./../..")`처럼 기준 element의 조상을 찾는 XPath가 하위 요소 조회로 잘못 처리되던 문제를 수정했습니다. nodriver의 CDP DOM tree를 직접 따라가므로 SVG `path`에서 상위 버튼을 찾는 흐름도 지원합니다. / Fixes relative parent XPath lookups such as `./../..` by traversing nodriver's CDP DOM tree directly, including SVG path-to-button lookup flows.
- **회귀 테스트 / Regression coverage:** 단위 테스트와 실제 Chrome 조상 탐색 smoke test를 추가했습니다. / Adds unit and real-Chrome ancestor lookup coverage.

## 0.1.6 업데이트 내역 / Release Notes

- **구버전 Chrome XPath / Legacy Chrome XPath:** 전역 XPath 조회가 nodriver `Tab.xpath()`의 `DOM.enable` 호출에 의존하지 않도록 변경했습니다. `DOM.getDocument`, `performSearch`, `getSearchResults`를 직접 사용하여 `DOM.enable wasn't found` 오류가 발생하는 구버전 target을 지원합니다. / Global XPath no longer depends on nodriver `Tab.xpath()` or `DOM.enable`; it directly uses DOM search commands for older targets that reject `DOM.enable`.
- **실제 Chrome 검증 / Real-Chrome verification:** `DOM.enable`을 거부하는 감시 상태에서 텍스트 기반 button XPath 조회를 검증했습니다. / Verifies button XPath lookup while explicitly rejecting any `DOM.enable` call.

## 0.1.7 업데이트 내역 / Release Notes

- **스크롤 좌표 보정 / Scrolled coordinate correction:** `ActionChains.move_to_element()`와 `move_to_element_with_offset()`이 입력 전에 대상 element를 화면 안으로 이동하고, CDP 입력에 문서 전체 좌표가 아닌 viewport 좌표를 사용합니다. 스크롤된 페이지에서 터치나 마우스 입력이 화면 밖 또는 잘못된 위치로 전달되던 문제를 수정합니다. / `ActionChains.move_to_element()` and `move_to_element_with_offset()` now bring the target into view before input and use viewport coordinates for CDP events, fixing touch and mouse input sent outside the viewport or to the wrong location on scrolled pages.
- **터치 스크롤 안정화 / Touch scrolling:** `WebElement.touch_click()`이 한 번의 swipe로 중단하지 않고 제한된 횟수 안에서 대상이 viewport에 들어올 때까지 스크롤합니다. / `WebElement.touch_click()` now scrolls until the target enters the viewport within the configured swipe limit instead of stopping after one swipe.
- **DOM 프로퍼티 호환 / DOM property compatibility:** `get_attribute()`가 일반 HTML attribute에 없는 `outerHTML`, `innerText` 등의 DOM property로 fallback합니다. Selenium 이식 코드의 클릭 전후 상태 검증이 `None`으로 오판되는 문제를 수정합니다. / `get_attribute()` now falls back to DOM properties such as `outerHTML` and `innerText` when no HTML attribute exists, preventing Selenium migration code from misreading state checks as `None`.
- **터치 드래그 좌표 / Touch drag coordinates:** touch drag 및 offset drag도 viewport 좌표를 사용하도록 통일했습니다. / Touch drag and offset-drag operations now consistently use viewport coordinates.
- **실제 Chrome 검증 / Real-Chrome verification:** 긴 모바일 페이지의 화면 밖 button을 스크롤한 뒤 offset touch로 클릭하고 `outerHTML` 상태 변화를 확인하는 smoke test를 추가했습니다. / Adds a real-Chrome smoke test that scrolls to an off-screen button on a long mobile page, performs an offset touch, and verifies its `outerHTML` state change.

## 0.1.8 업데이트 내역 / Release Notes

- **클릭 예외 호환 / Click exception compatibility:** Selenium 이식 코드에서 참조하는 `ElementNotInteractableException`을 공개 예외로 추가했습니다. / Adds the public `ElementNotInteractableException` expected by Selenium migration code.
- **Auto-wait 오류 구분 / Auto-wait error semantics:** auto-wait 이후에도 element가 숨김 또는 비활성 상태이면 일반 `TimeoutException` 대신 `ElementNotInteractableException`을 발생시킵니다. / Raises `ElementNotInteractableException` instead of a generic `TimeoutException` when an element remains hidden or disabled after auto-wait.
- **회귀 테스트 / Regression coverage:** 숨겨진 element 클릭과 공개 예외 import를 검증하는 테스트를 추가했습니다. / Adds regression coverage for hidden-element clicks and the public exception import.

## 빠른 시작 / Quick Start

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

## 클릭과 입력 방식 / Click and Input Modes

`selenodriver`는 클릭 방식을 의도적으로 분리합니다.

`selenodriver` intentionally exposes each click mechanism separately.

| 방식 / Mode | 사용 예 / API | 내부 동작 / Implementation | 용도 / Use case |
| --- | --- | --- | --- |
| 기본/마우스 클릭 / Default mouse | `element.click()` | CDP `Input.dispatchMouseEvent` | 일반 데스크톱 클릭 / Desktop interaction |
| 명시적 마우스 클릭 / Explicit mouse | `element.mouse_click()` | CDP `mousePressed` / `mouseReleased` | 기본 클릭과 동일 / Explicit mouse control |
| 터치 클릭 / Touch | `element.touch_click()` | CDP `Input.dispatchTouchEvent` | 모바일 탭 / Mobile tap behavior |
| JS 클릭 / JavaScript | `element.js_click()` | JS `el.click()` | DOM 직접 호출 / Direct DOM activation |

기본 클릭은 element의 화면상 중앙 좌표를 기준으로 마우스 이벤트를 보냅니다. JS 클릭이 필요한 경우에는 `js_click()`을 별도로 호출합니다.

The default click sends mouse events to the element's visual center. Call `js_click()` explicitly when direct DOM activation is required.

## 좌표 클릭 / 랜덤 위치 클릭 / Offset and Randomized Clicks

Selenium의 `ActionChains` 스타일로 element 중앙이 아닌 지점을 클릭할 수 있습니다.

Selenium-style `ActionChains` can click a point away from the element center.

```python
from selenodriver import ActionChains

ActionChains(driver) \
    .move_to_element_with_offset(element, xoffset, yoffset) \
    .click() \
    .perform()
```

`xoffset`, `yoffset`은 Selenium 호환 기준으로 element의 중앙점 기준입니다.

For Selenium compatibility, `xoffset` and `yoffset` are measured from the element center.

element 내부의 랜덤 위치를 클릭하려면 좌상단 기준 랜덤 좌표를 만든 뒤 중앙점 기준 offset으로 변환합니다.

To click a randomized point inside an element, generate top-left-relative coordinates and convert them to center-relative offsets.

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

The same point can be activated with touch input.

```python
ActionChains(driver) \
    .touch_move_to_element_with_offset(element, xoffset, yoffset) \
    .touch_click() \
    .perform()
```

## 모바일 관련 기능 / Mobile Features

모바일 테스트를 위해 다음 기능을 제공합니다.

The following APIs support mobile-oriented testing.

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

The mobile emulation extension applies UA, viewport, device scale factor, touch emulation, locale, and timezone through CDP `Emulation.*` commands. Settings are reapplied after attach, navigation, context changes, and new-tab discovery.

```python
from selenodriver import Chrome, MobileEmulationExtension

driver = Chrome(
    extensions=[
        MobileEmulationExtension("android")
    ]
)
```

직접 프로필 dict도 사용할 수 있습니다.

Custom profile dictionaries are also supported.

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

## 현재 구현 범위 / Implementation Status

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
- input modes: `WebElement.send_keys()` uses CDP keyboard events by default; `WebElement.send_keys_js()` is available when JavaScript value mutation is explicitly required. The same CDP path works with desktop and mobile emulation.
- expected conditions: `presence_of_element_located`, `visibility_of_element_located`, `element_to_be_clickable`, `invisibility_of_element_located`, `alert_is_present`, `title_is`, `title_contains`, `url_contains`, `url_to_be`, `url_matches`, text checks, and window count checks

더 자세한 사용법은 [한국어 가이드](https://github.com/L1V1N-ST0N3/selenodriver/blob/master/GUIDE.md)와 [English guide](https://github.com/L1V1N-ST0N3/selenodriver/blob/master/GUIDE_EN.md)에 정리되어 있습니다.

For complete usage details, see the [Korean guide](https://github.com/L1V1N-ST0N3/selenodriver/blob/master/GUIDE.md) or the [English guide](https://github.com/L1V1N-ST0N3/selenodriver/blob/master/GUIDE_EN.md).

## License

This project is licensed under the GNU Affero General Public License v3.0.

이 프로젝트는 GNU Affero General Public License v3.0으로 배포됩니다.

`selenodriver` depends on `nodriver`, which is licensed under AGPL-3.0, so this project follows the same license family.

## 개발 / Development

PyPI에서 설치 / Install from PyPI:

```powershell
python -m pip install selenodriver
```

로컬 개발 및 테스트 / Local development and tests:

```powershell
python -m pip install -e .
python -m pip install pytest
pytest
```

실제 브라우저 smoke test / Real-browser smoke tests:

```powershell
$env:SELENODRIVER_RUN_SMOKE='1'
pytest -m smoke
```
