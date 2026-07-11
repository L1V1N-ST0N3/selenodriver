# selenodriver 패치 메모 (0.1.1 후보)

실사용(`restoreAccount_login_cafe_nodriver.py`)에서 확인된 장애를 기준으로 정리한 수정 목록입니다.
우선순위 높은 항목부터 반영하면 됩니다.

---

## 배경에서 터진 증상

| 증상 | 직접 원인 |
|------|-----------|
| `Se-Authorization 토큰을 찾지 못했습니다` | `get_cookies()`가 쿠키를 제대로 못 넘겨 `requests.Session`이 비로그인 상태 |
| `SyntaxError: Illegal return statement` / UA 헤더에 ExceptionDetails | `execute_script("return ...")`가 Selenium처럼 function 본문으로 실행되지 않음 |
| `TypeError: unhashable type: 'RemoteObject'` (`_wait_for_page_load`) | `document.readyState` 평가 결과가 문자열이 아니라 CDP `RemoteObject` |

---

## 1. `execute_script` Selenium 호환 (필수)

**파일:** `src/selenodriver/driver.py`

### 문제
- 무인자 경로가 `tab.evaluate(script)`라서 top-level `return`이 문법 오류
- 표현식만 넘기는 내부 호출(`document.readyState`)과 Selenium식 `return ...`를 동시에 지원해야 함
- nodriver가 값을 못 풀면 `RemoteObject` / `ExceptionDetails`를 그대로 반환하는 경우가 있음

### 개선안
```python
def execute_script(self, script: str, *args):
    if args:
        return self._normalize_script_result(self._execute_script_with_args(script, *args))

    import re
    body = script or ""
    if re.search(r"(^|\n)\s*return\b", body):
        wrapped = f"(function(){{ {body}\n }})()"
    else:
        wrapped = f"(function(){{ return ({body}); }})()"
    return self._normalize_script_result(
        self._runner.run(self._tab.evaluate(wrapped, return_by_value=True))
    )

@staticmethod
def _normalize_script_result(value):
    if value is None:
        return None
    name = type(value).__name__
    if name == "ExceptionDetails":
        raise SelenoDriverException(str(value))
    if name == "RemoteObject":
        raw = getattr(value, "value", None)
        if raw is not None:
            return raw
        deep = getattr(value, "deep_serialized_value", None)
        if deep is not None and getattr(deep, "value", None) is not None:
            return deep.value
        return None
    return value
```

### 테스트
- `execute_script("return 1")` → `1`
- `execute_script("document.readyState")` → `"complete"` 등 문자열
- `driver.get(url)` 후 `_wait_for_page_load`가 RemoteObject로 죽지 않을 것

> 참고: `nodriver_project` 로컬 소스에는 위 로직이 일부 이미 들어가 있음. **배포/설치본(site-packages)에도 반영·재설치 필요.**

---

## 2. `get_cookies` 강화 (필수)

**파일:** `src/selenodriver/driver.py`

### 문제
- 현재: `Network.getCookies([current_url])`만 사용
- URL/도메인 조건에 따라 `NID_AUT` 등이 빠질 수 있음
- 예전 커스텀 shim은 `get_all_cookies()` 결과를 `result.cookies`로 읽어 **항상 빈 리스트**가 되기도 했음
  (`page.send()`는 이미 `list[Cookie]`를 반환)

### 개선안
```python
def get_cookies(self) -> list[dict]:
    from nodriver import cdp

    cookies = []
    try:
        cookies = self._runner.run(
            self._tab.send(cdp.network.get_cookies([self.current_url]))
        ) or []
    except Exception:
        cookies = []

    if not cookies:
        try:
            cookies = self._runner.run(
                self._tab.send(cdp.network.get_all_cookies())
            ) or []
        except Exception:
            cookies = []

    if not isinstance(cookies, list):
        cookies = getattr(cookies, "cookies", None) or []

    return [self._cookie_to_dict(c) for c in cookies]
```

### 테스트
- 네이버 로그인 후 `any(c["name"] == "NID_AUT" for c in driver.get_cookies())`
- 쿠키를 `requests.Session`에 옮긴 뒤 `PostWriteFormSeOptions.naver`에서 token 존재

---

## 3. Options: `--user-data-dir` 인자 파싱

**파일:** `src/selenodriver/options.py`

### 문제
- Selenium 이식 코드는 보통 `options.add_argument("--user-data-dir=...")`를 씀
- 지금은 `set_user_data_dir()`만 `user_data_dir` kwargs로 전달됨
- 인자로만 넣으면 nodriver `user_data_dir` 전용 경로와 어긋날 수 있음

### 개선안 (`to_nodriver_kwargs`)
```python
def to_nodriver_kwargs(self) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    browser_args = []
    user_data_dir = self._user_data_dir

    for arg in self.arguments:
        if arg.startswith("--user-data-dir="):
            user_data_dir = arg.split("=", 1)[1]
        else:
            browser_args.append(arg)

    if browser_args:
        kwargs["browser_args"] = browser_args
    if user_data_dir is not None:
        kwargs["user_data_dir"] = user_data_dir
    # ... binary / headless / lang / prefs 기존 로직 유지
    return kwargs
```

---

## 4. Selenium 예외 / alert 호환

**파일:** `exceptions.py`, `driver.py` (`SwitchTo`), `wait.py`, `expected_conditions.py`

### 추가 예외 (권장)
- `WebDriverException` (또는 기존 `SelenoDriverException` alias)
- `NoAlertPresentException`
- (여유 있으면) `StaleElementReferenceException`, `ElementClickInterceptedException`

### alert
- `switch_to.alert` 접근 시 `_current_alert is None`이면 `NoAlertPresentException`
- `EC.alert_is_present`는 예외를 던지지 않고 `False` 반환
- `WebDriverWait` 기본 ignored에 alert 관련 예외를 넣을지, EC 쪽에서만 안전하게 처리할지 정책을 하나로 정할 것

---

## 5. `execute_cdp_cmd` 호환 래퍼

**파일:** `src/selenodriver/driver.py`

### 문제
- Selenium 코드: `driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "..."})`
- 현재: `send_cdp(cdp.page.add_script_to_evaluate_on_new_document(...))` / `add_init_script(...)`

### 개선안
- 자주 쓰는 명령만 매핑해도 충분
  - `Page.addScriptToEvaluateOnNewDocument` → `add_init_script`
  - 그 외는 `send_cdp` 또는 “미지원” 예외
- GUIDE에 `add_init_script`를 spoof/스텔스 기본 경로로 명시

---

## 6. ActionChains: modifier + 키 (권장)

**파일:** `src/selenodriver/action_chains.py`, `keys.py`

### 문제
- `key_down(CONTROL).send_keys("v")`가 실제 Ctrl+V(붙여넣기)가 아니라
  일반 문자면 `activeElement.value += 'v'` JS append로 처리됨
- 네이버 로그인 등은 클립보드 붙여넣기 패턴이 흔함

### 개선안 (택1)
1. modifier 상태를 추적해 Control 눌린 동안은 CDP `dispatchKeyEvent`로 처리
2. 또는 GUIDE에 “Ctrl+V 붙여넣기는 OS 입력/별도 helper 권장”으로 명시하고 예제 제공

---

## 7. `_wait_for_page_load` 방어

**파일:** `src/selenodriver/driver.py`

### 개선안
```python
ready_state = self.execute_script("document.readyState")
if not isinstance(ready_state, str):
    ready_state = str(getattr(ready_state, "value", "") or "")
if ready_state in accepted:
    return
```
`execute_script` 정규화(1번)가 제대로면 여기까지 거의 안 오지만, 이중 방어로 두는 편이 안전.

---

## 8. 문서 / 버전 / 테스트

### 문서
- `README.md` / `GUIDE.md`
  - `execute_script` return/표현식 동작
  - `get_cookies` 범위
  - `add_init_script` vs CDP
  - Options `user-data-dir` 두 가지 넣는 법

### 버전
- `pyproject.toml` / README: `0.1.0` → `0.1.1`

### 테스트 (최소)
```text
tests/test_execute_script_compat.py
  - return 스타일
  - 표현식 스타일
  - ExceptionDetails → 예외

tests/test_cookies.py
  - list[dict] 형태
  - current_url 실패 시 all_cookies fallback (mock)

tests/test_page_load.py  (smoke)
  - get() 후 readyState 문자열 비교
```

---

## 패치 적용 체크리스트

- [x] `execute_script` wrap + `_normalize_script_result`
- [x] `get_cookies` current_url → all_cookies fallback, 항상 list
- [x] Options `--user-data-dir=` 파싱
- [x] `NoAlertPresentException` + alert/EC/Wait 정리
- [x] `execute_cdp_cmd` 또는 문서에 `add_init_script` 안내
- [x] ActionChains Ctrl+V 정책 결정(구현 or 문서)
- [x] `_wait_for_page_load` 타입 방어
- [x] 버전 `0.1.1` + GUIDE/README 반영
- [x] 단위/스모크 테스트
- [ ] `pip install -e .` 또는 wheel 재배포 후 ranks 환경(`D:\Onedot\...`)에 설치

---

## 앱 쪽 임시 우회 (이미 적용된 것)

`restoreAccount_login_cafe_nodriver.py`의 `ChromeCompat`에 아래가 들어가 있음.
라이브러리 0.1.1이 배포되면 앱 쪽 중복 래핑은 줄여도 됨.

- `execute_script` return/표현식 분기 + RemoteObject unwrap
- `get_cookies` fallback
- alert `NoAlertPresentException`
- Ctrl+V는 `pyautogui` 유지 (로그인 안정성)

---

## 권장 반영 순서

1. `execute_script` + page load 방어
2. `get_cookies`
3. Options user-data-dir
4. 예외/alert
5. CDP 호환·ActionChains·문서·버전
