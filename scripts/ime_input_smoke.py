from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

from selenodriver import By, Chrome


CASES = [
    "한글",
    "한글abc",
    "한글123",
    "한글!@#",
    "한글abc123!@😀",
    "abc한글테스트123",
    "가족👨‍👩‍👧‍👦테스트",
]

HTML = """<!doctype html>
<meta charset="utf-8">
<title>selenodriver CDP IME smoke</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 32px; }
  textarea { width: min(900px, 90vw); height: 180px; font-size: 24px; padding: 12px; }
  pre { white-space: pre-wrap; background: #f3f4f6; padding: 12px; }
</style>
<h1>selenodriver CDP IME smoke</h1>
<textarea id="target" autofocus></textarea>
<pre id="state"></pre>
<script>
  window.__events = [];
  const target = document.getElementById('target');
  const state = document.getElementById('state');
  for (const type of ['keydown', 'beforeinput', 'compositionstart', 'compositionupdate',
                      'compositionend', 'input', 'keyup', 'change']) {
    target.addEventListener(type, event => {
      window.__events.push({
        type,
        key: event.key || null,
        data: event.data || null,
        inputType: event.inputType || null,
        value: target.value,
        isComposing: !!event.isComposing,
      });
      state.textContent = JSON.stringify(window.__events.slice(-12), null, 2);
    });
  }
</script>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run visible CDP IME smoke tests")
    parser.add_argument("--delay", type=float, default=0.08, help="Delay between input events")
    parser.add_argument("--startup-wait", type=float, default=1.0, help="Seconds to wait before input")
    parser.add_argument("--keep-open", action="store_true", help="Keep Chrome open after the report")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("ignore/ime_smoke_report.json"),
        help="JSON report path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    driver = Chrome(headless=False)
    results: list[dict] = []
    try:
        driver.get("data:text/html;charset=utf-8," + quote(HTML))
        print(f"Chrome opened. Waiting {args.startup_wait:.1f} seconds before input.")
        time.sleep(args.startup_wait)
        target = driver.find_element(By.ID, "target")
        target.mouse_click()
        diagnostics = driver.execute_script(
            """
            const el = arguments[0];
            const rect = el.getBoundingClientRect();
            const borderX = Math.max(0, (window.outerWidth - window.innerWidth) / 2);
            const chromeY = Math.max(0, window.outerHeight - window.innerHeight - borderX);
            return {
                documentHasFocus: document.hasFocus(),
                activeElementId: document.activeElement && document.activeElement.id,
                screenX: window.screenX,
                screenY: window.screenY,
                outerWidth: window.outerWidth,
                outerHeight: window.outerHeight,
                innerWidth: window.innerWidth,
                innerHeight: window.innerHeight,
                clickX: window.screenX + borderX + rect.left + rect.width / 2,
                clickY: window.screenY + chromeY + rect.top + rect.height / 2,
            };
            """,
            target,
        )
        print("Diagnostics: " + json.dumps(diagnostics, ensure_ascii=False))

        for expected in CASES:
            target.mouse_click()
            target.clear()
            driver.execute_script("window.__events = []")
            started = time.perf_counter()
            error = None
            try:
                target.send_keys(expected, mode="jamo", delay=args.delay, focus=True)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            elapsed = time.perf_counter() - started
            time.sleep(0.2)
            actual = driver.execute_script("return arguments[0].value", target)
            events = driver.execute_script("return window.__events") or []
            result = {
                "expected": expected,
                "actual": actual,
                "passed": actual == expected and error is None,
                "error": error,
                "elapsed_seconds": round(elapsed, 3),
                "event_types": [event.get("type") for event in events],
                "events": events,
            }
            results.append(result)
            print(json.dumps({key: result[key] for key in (
                "expected", "actual", "passed", "error"
            )}, ensure_ascii=False))

        report = {
            "selenodriver_version": __import__("selenodriver").__version__,
            "delay": args.delay,
            "diagnostics": diagnostics,
            "passed": all(result["passed"] for result in results),
            "results": results,
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report: {args.report.resolve()}")
        print(f"Overall: {'PASS' if report['passed'] else 'FAIL'}")
        if args.keep_open:
            input("Press Enter to close Chrome...")
        return 0 if report["passed"] else 1
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())
