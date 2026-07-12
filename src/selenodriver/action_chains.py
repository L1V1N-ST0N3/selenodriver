from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .element import WebElement
from .keys import Keys, dispatch_key, dispatch_key_press, dispatch_text, is_special_key, split_key_sequence


_MODIFIER_BITS = {Keys.ALT: 1, Keys.CONTROL: 2, Keys.META: 4, Keys.COMMAND: 4, Keys.SHIFT: 8}


class ActionChains:
    def __init__(self, driver: Any, duration: int = 250):
        self._driver = driver
        self._duration = duration
        self._actions: list[Callable[[], None]] = []
        self._x = 0
        self._y = 0
        self._modifiers: set[str] = set()

    def perform(self) -> None:
        try:
            for action in self._actions:
                action()
        finally:
            self.reset_actions()

    def reset_actions(self) -> None:
        self._actions.clear()
        self._modifiers.clear()

    def click(
        self,
        on_element: WebElement | None = None,
        *,
        input_type: str = "mouse",
        use_touch: bool = False,
    ) -> "ActionChains":
        def _action() -> None:
            selected_input = "touch" if use_touch else input_type
            if on_element is not None:
                if selected_input == "touch":
                    on_element.touch_click()
                    return
                if selected_input == "js":
                    on_element.js_click()
                    return
                if selected_input != "mouse":
                    raise ValueError("input_type must be 'mouse', 'touch', or 'js'")
                on_element.click()
                return
            if selected_input == "touch":
                self._touch_event()
                return
            if selected_input == "js":
                raise ValueError("ActionChains.click(input_type='js') requires on_element")
            if selected_input != "mouse":
                raise ValueError("input_type must be 'mouse', 'touch', or 'js'")
            self._mouse_event("mousePressed", button="left", buttons=1, click_count=1)
            self._mouse_event("mouseReleased", button="left", buttons=0, click_count=1)

        self._actions.append(_action)
        return self

    def touch_click(self, on_element: WebElement | None = None) -> "ActionChains":
        return self.click(on_element, input_type="touch")

    def double_click(self, on_element: WebElement | None = None, *, input_type: str = "mouse") -> "ActionChains":
        def _action() -> None:
            if input_type == "touch":
                if on_element is not None:
                    self._set_position_from_element(on_element)
                self._touch_event()
                self._touch_event()
                return
            if input_type != "mouse":
                raise ValueError("input_type must be 'mouse' or 'touch'")
            if on_element is not None:
                on_element._runner.run(on_element.raw.mouse_move())
                on_element._runner.run(on_element.raw.mouse_click(button="left"))
                on_element._runner.run(on_element.raw.mouse_click(button="left"))
                return
            self._mouse_event("mousePressed", button="left", buttons=1, click_count=2)
            self._mouse_event("mouseReleased", button="left", buttons=0, click_count=2)

        self._actions.append(_action)
        return self

    def double_tap(self, on_element: WebElement | None = None) -> "ActionChains":
        return self.double_click(on_element, input_type="touch")

    def context_click(self, on_element: WebElement | None = None) -> "ActionChains":
        def _action() -> None:
            if on_element is not None:
                on_element._runner.run(on_element.raw.mouse_click(button="right", buttons=2))
                return
            self._mouse_event("mousePressed", button="right", buttons=2, click_count=1)
            self._mouse_event("mouseReleased", button="right", buttons=0, click_count=1)

        self._actions.append(_action)
        return self

    def move_to_element(self, to_element: WebElement, *, input_type: str = "mouse") -> "ActionChains":
        def _action() -> None:
            self._set_position_from_element(to_element)
            if input_type == "mouse":
                self._mouse_event("mouseMoved")
                return
            if input_type == "touch":
                return
            raise ValueError("input_type must be 'mouse' or 'touch'")

        self._actions.append(_action)
        return self

    def move_to_element_with_offset(
        self,
        to_element: WebElement,
        xoffset: int,
        yoffset: int,
        *,
        input_type: str = "mouse",
    ) -> "ActionChains":
        def _action() -> None:
            rect = to_element.rect
            self._x = rect["x"] + rect["width"] / 2 + int(xoffset)
            self._y = rect["y"] + rect["height"] / 2 + int(yoffset)
            if input_type == "mouse":
                self._mouse_event("mouseMoved")
                return
            if input_type == "touch":
                return
            raise ValueError("input_type must be 'mouse' or 'touch'")

        self._actions.append(_action)
        return self

    def touch_move_to_element_with_offset(self, to_element: WebElement, xoffset: int, yoffset: int) -> "ActionChains":
        return self.move_to_element_with_offset(to_element, xoffset, yoffset, input_type="touch")

    def move_by_offset(self, xoffset: int, yoffset: int) -> "ActionChains":
        def _action() -> None:
            self._x += xoffset
            self._y += yoffset
            self._mouse_event("mouseMoved")

        self._actions.append(_action)
        return self

    def drag_and_drop(self, source: WebElement, target: WebElement) -> "ActionChains":
        self._actions.append(lambda: source._runner.run(source.raw.mouse_drag(target.raw)))
        return self

    def drag_and_drop_by_offset(self, source: WebElement, xoffset: int, yoffset: int) -> "ActionChains":
        self._actions.append(lambda: source._runner.run(source.raw.mouse_drag((xoffset, yoffset), relative=True)))
        return self

    def touch_drag_and_drop(self, source: WebElement, target: WebElement, *, steps: int = 8) -> "ActionChains":
        def _action() -> None:
            source_rect = source.rect
            target_rect = target.rect
            start_x = source_rect["x"] + source_rect["width"] / 2
            start_y = source_rect["y"] + source_rect["height"] / 2
            end_x = target_rect["x"] + target_rect["width"] / 2
            end_y = target_rect["y"] + target_rect["height"] / 2
            self._touch_swipe(start_x, start_y, end_x, end_y, steps=steps)
            self._x = end_x
            self._y = end_y

        self._actions.append(_action)
        return self

    def touch_drag_by_offset(self, source: WebElement, xoffset: int, yoffset: int, *, steps: int = 8) -> "ActionChains":
        def _action() -> None:
            rect = source.rect
            start_x = rect["x"] + rect["width"] / 2
            start_y = rect["y"] + rect["height"] / 2
            end_x = start_x + int(xoffset)
            end_y = start_y + int(yoffset)
            self._touch_swipe(start_x, start_y, end_x, end_y, steps=steps)
            self._x = end_x
            self._y = end_y

        self._actions.append(_action)
        return self

    def click_and_hold(self, on_element: WebElement | None = None, *, input_type: str = "mouse") -> "ActionChains":
        def _action() -> None:
            if on_element is not None:
                self._set_position_from_element(on_element)
            if input_type == "touch":
                self._touch_start()
                return
            if input_type != "mouse":
                raise ValueError("input_type must be 'mouse' or 'touch'")
            self._mouse_event("mouseMoved")
            self._mouse_event("mousePressed", button="left", buttons=1, click_count=1)

        self._actions.append(_action)
        return self

    def long_press(self, on_element: WebElement | None = None, seconds: float = 0.5) -> "ActionChains":
        return self.click_and_hold(on_element, input_type="touch").pause(seconds).release(input_type="touch")

    def release(self, on_element: WebElement | None = None, *, input_type: str = "mouse") -> "ActionChains":
        def _action() -> None:
            if on_element is not None:
                self._set_position_from_element(on_element)
            if input_type == "touch":
                self._touch_end()
                return
            if input_type != "mouse":
                raise ValueError("input_type must be 'mouse' or 'touch'")
            self._mouse_event("mouseMoved")
            self._mouse_event("mouseReleased", button="left", buttons=0, click_count=1)

        self._actions.append(_action)
        return self

    def send_keys(self, *keys_to_send: object) -> "ActionChains":
        self._actions.append(lambda: self._send_keys(*keys_to_send))
        return self

    def send_keys_to_element(self, element: WebElement, *keys_to_send: object) -> "ActionChains":
        def _action() -> None:
            element._runner.run(element.raw.focus())
            element.send_keys(*keys_to_send)

        self._actions.append(_action)
        return self

    def key_down(self, value: str, element: WebElement | None = None) -> "ActionChains":
        def _action() -> None:
            if element is not None:
                element._runner.run(element.raw.focus())
            if value in _MODIFIER_BITS:
                self._modifiers.add(value)
            dispatch_key(self._driver.raw_tab, self._driver._runner, value, "keyDown", self._modifier_mask())

        self._actions.append(_action)
        return self

    def key_up(self, value: str, element: WebElement | None = None) -> "ActionChains":
        def _action() -> None:
            if element is not None:
                element._runner.run(element.raw.focus())
            dispatch_key(self._driver.raw_tab, self._driver._runner, value, "keyUp", self._modifier_mask())
            self._modifiers.discard(value)

        self._actions.append(_action)
        return self

    def pause(self, seconds: float) -> "ActionChains":
        def _action() -> None:
            sleep = getattr(self._driver.raw_tab, "sleep", None)
            if sleep is not None:
                self._driver._runner.run(sleep(seconds))
                return
            import time

            time.sleep(seconds)

        self._actions.append(_action)
        return self

    def _send_keys(self, *values: object) -> None:
        for chunk in split_key_sequence(*values):
            if is_special_key(chunk):
                dispatch_key_press(self._driver.raw_tab, self._driver._runner, chunk, self._modifier_mask())
            elif self._modifiers:
                dispatch_text(self._driver.raw_tab, self._driver._runner, chunk, self._modifier_mask())
            else:
                dispatch_text(self._driver.raw_tab, self._driver._runner, chunk)

    def _modifier_mask(self) -> int:
        return sum(_MODIFIER_BITS[value] for value in self._modifiers)

    def _mouse_event(self, type_: str, *, button: str | None = None, buttons: int | None = None, click_count: int | None = None) -> None:
        from nodriver import cdp

        event = cdp.input_.dispatch_mouse_event(
            type_,
            x=self._x,
            y=self._y,
            button=cdp.input_.MouseButton(button) if button is not None else None,
            buttons=buttons,
            click_count=click_count,
        )
        self._driver._runner.run(self._driver.raw_tab.send(event))

    def _touch_event(self) -> None:
        self._touch_start()
        self._touch_end()

    def _touch_start(self) -> None:
        from nodriver import cdp

        point = cdp.input_.TouchPoint(x=self._x, y=self._y, radius_x=1, radius_y=1, force=1, id_=1)
        touch_start = cdp.input_.dispatch_touch_event("touchStart", [point])
        self._driver._runner.run(self._driver.raw_tab.send(touch_start))

    def _touch_move(self, x: float, y: float) -> None:
        from nodriver import cdp

        point = cdp.input_.TouchPoint(x=x, y=y, radius_x=1, radius_y=1, force=1, id_=1)
        self._driver._runner.run(self._driver.raw_tab.send(cdp.input_.dispatch_touch_event("touchMove", [point])))

    def _touch_end(self) -> None:
        from nodriver import cdp

        self._driver._runner.run(self._driver.raw_tab.send(cdp.input_.dispatch_touch_event("touchEnd", [])))

    def _touch_swipe(self, start_x: float, start_y: float, end_x: float, end_y: float, *, steps: int = 8) -> None:
        steps = max(1, int(steps))
        self._x = start_x
        self._y = start_y
        self._touch_start()
        for index in range(1, steps + 1):
            ratio = index / steps
            self._touch_move(start_x + (end_x - start_x) * ratio, start_y + (end_y - start_y) * ratio)
        self._touch_end()

    def _set_position_from_element(self, element: WebElement) -> None:
        rect = element.rect
        self._x = rect["x"] + rect["width"] / 2
        self._y = rect["y"] + rect["height"] / 2
