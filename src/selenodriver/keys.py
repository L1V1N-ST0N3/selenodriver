from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator


class Keys:
    NULL = "\ue000"
    CANCEL = "\ue001"
    HELP = "\ue002"
    BACKSPACE = "\ue003"
    BACK_SPACE = BACKSPACE
    TAB = "\ue004"
    CLEAR = "\ue005"
    RETURN = "\ue006"
    ENTER = "\ue007"
    SHIFT = "\ue008"
    LEFT_SHIFT = SHIFT
    CONTROL = "\ue009"
    LEFT_CONTROL = CONTROL
    ALT = "\ue00a"
    LEFT_ALT = ALT
    PAUSE = "\ue00b"
    ESCAPE = "\ue00c"
    SPACE = "\ue00d"
    PAGE_UP = "\ue00e"
    PAGE_DOWN = "\ue00f"
    END = "\ue010"
    HOME = "\ue011"
    LEFT = "\ue012"
    ARROW_LEFT = LEFT
    UP = "\ue013"
    ARROW_UP = UP
    RIGHT = "\ue014"
    ARROW_RIGHT = RIGHT
    DOWN = "\ue015"
    ARROW_DOWN = DOWN
    INSERT = "\ue016"
    DELETE = "\ue017"
    SEMICOLON = "\ue018"
    EQUALS = "\ue019"
    NUMPAD0 = "\ue01a"
    NUMPAD1 = "\ue01b"
    NUMPAD2 = "\ue01c"
    NUMPAD3 = "\ue01d"
    NUMPAD4 = "\ue01e"
    NUMPAD5 = "\ue01f"
    NUMPAD6 = "\ue020"
    NUMPAD7 = "\ue021"
    NUMPAD8 = "\ue022"
    NUMPAD9 = "\ue023"
    MULTIPLY = "\ue024"
    ADD = "\ue025"
    SEPARATOR = "\ue026"
    SUBTRACT = "\ue027"
    DECIMAL = "\ue028"
    DIVIDE = "\ue029"
    F1 = "\ue031"
    F2 = "\ue032"
    F3 = "\ue033"
    F4 = "\ue034"
    F5 = "\ue035"
    F6 = "\ue036"
    F7 = "\ue037"
    F8 = "\ue038"
    F9 = "\ue039"
    F10 = "\ue03a"
    F11 = "\ue03b"
    F12 = "\ue03c"
    META = "\ue03d"
    COMMAND = META


@dataclass(frozen=True)
class KeyDefinition:
    key: str
    code: str | None = None
    windows_virtual_key_code: int | None = None
    text: str | None = None


KEY_DEFINITIONS: dict[str, KeyDefinition] = {
    Keys.BACKSPACE: KeyDefinition("Backspace", "Backspace", 8),
    Keys.TAB: KeyDefinition("Tab", "Tab", 9, "\t"),
    Keys.CLEAR: KeyDefinition("Clear", "Clear", 12),
    Keys.RETURN: KeyDefinition("Enter", "Enter", 13, "\r"),
    Keys.ENTER: KeyDefinition("Enter", "Enter", 13, "\r"),
    Keys.SHIFT: KeyDefinition("Shift", "ShiftLeft", 16),
    Keys.CONTROL: KeyDefinition("Control", "ControlLeft", 17),
    Keys.ALT: KeyDefinition("Alt", "AltLeft", 18),
    Keys.PAUSE: KeyDefinition("Pause", "Pause", 19),
    Keys.ESCAPE: KeyDefinition("Escape", "Escape", 27),
    Keys.SPACE: KeyDefinition(" ", "Space", 32, " "),
    Keys.PAGE_UP: KeyDefinition("PageUp", "PageUp", 33),
    Keys.PAGE_DOWN: KeyDefinition("PageDown", "PageDown", 34),
    Keys.END: KeyDefinition("End", "End", 35),
    Keys.HOME: KeyDefinition("Home", "Home", 36),
    Keys.LEFT: KeyDefinition("ArrowLeft", "ArrowLeft", 37),
    Keys.UP: KeyDefinition("ArrowUp", "ArrowUp", 38),
    Keys.RIGHT: KeyDefinition("ArrowRight", "ArrowRight", 39),
    Keys.DOWN: KeyDefinition("ArrowDown", "ArrowDown", 40),
    Keys.INSERT: KeyDefinition("Insert", "Insert", 45),
    Keys.DELETE: KeyDefinition("Delete", "Delete", 46),
    Keys.SEMICOLON: KeyDefinition(";", "Semicolon", 186, ";"),
    Keys.EQUALS: KeyDefinition("=", "Equal", 187, "="),
    Keys.NUMPAD0: KeyDefinition("0", "Numpad0", 96, "0"),
    Keys.NUMPAD1: KeyDefinition("1", "Numpad1", 97, "1"),
    Keys.NUMPAD2: KeyDefinition("2", "Numpad2", 98, "2"),
    Keys.NUMPAD3: KeyDefinition("3", "Numpad3", 99, "3"),
    Keys.NUMPAD4: KeyDefinition("4", "Numpad4", 100, "4"),
    Keys.NUMPAD5: KeyDefinition("5", "Numpad5", 101, "5"),
    Keys.NUMPAD6: KeyDefinition("6", "Numpad6", 102, "6"),
    Keys.NUMPAD7: KeyDefinition("7", "Numpad7", 103, "7"),
    Keys.NUMPAD8: KeyDefinition("8", "Numpad8", 104, "8"),
    Keys.NUMPAD9: KeyDefinition("9", "Numpad9", 105, "9"),
    Keys.MULTIPLY: KeyDefinition("*", "NumpadMultiply", 106, "*"),
    Keys.ADD: KeyDefinition("+", "NumpadAdd", 107, "+"),
    Keys.SEPARATOR: KeyDefinition(",", "NumpadComma", 108, ","),
    Keys.SUBTRACT: KeyDefinition("-", "NumpadSubtract", 109, "-"),
    Keys.DECIMAL: KeyDefinition(".", "NumpadDecimal", 110, "."),
    Keys.DIVIDE: KeyDefinition("/", "NumpadDivide", 111, "/"),
    Keys.F1: KeyDefinition("F1", "F1", 112),
    Keys.F2: KeyDefinition("F2", "F2", 113),
    Keys.F3: KeyDefinition("F3", "F3", 114),
    Keys.F4: KeyDefinition("F4", "F4", 115),
    Keys.F5: KeyDefinition("F5", "F5", 116),
    Keys.F6: KeyDefinition("F6", "F6", 117),
    Keys.F7: KeyDefinition("F7", "F7", 118),
    Keys.F8: KeyDefinition("F8", "F8", 119),
    Keys.F9: KeyDefinition("F9", "F9", 120),
    Keys.F10: KeyDefinition("F10", "F10", 121),
    Keys.F11: KeyDefinition("F11", "F11", 122),
    Keys.F12: KeyDefinition("F12", "F12", 123),
    Keys.META: KeyDefinition("Meta", "MetaLeft", 91),
}


def is_special_key(value: str) -> bool:
    return value in KEY_DEFINITIONS or value == Keys.NULL


def split_key_sequence(*values: object) -> Iterator[str]:
    buffer: list[str] = []
    for value in values:
        for char in str(value):
            if is_special_key(char):
                if buffer:
                    yield "".join(buffer)
                    buffer.clear()
                if char != Keys.NULL:
                    yield char
            else:
                buffer.append(char)
    if buffer:
        yield "".join(buffer)


def dispatch_key(tab: Any, runner: Any, value: str, type_: str = "keyDown", modifiers: int = 0) -> None:
    from nodriver import cdp

    definition = KEY_DEFINITIONS.get(value)
    if definition is None:
        definition = KeyDefinition(value, None, ord(value) if len(value) == 1 else None, value if len(value) == 1 else None)
    event = cdp.input_.dispatch_key_event(
        type_,
        text=definition.text if type_ == "keyDown" else None,
        unmodified_text=definition.text if type_ == "keyDown" else None,
        key=definition.key,
        code=definition.code,
        windows_virtual_key_code=definition.windows_virtual_key_code,
        modifiers=modifiers,
    )
    runner.run(tab.send(event))


def dispatch_text(tab: Any, runner: Any, value: str, modifiers: int = 0) -> None:
    """Send text as real CDP keyboard events, one logical character at a time."""
    for char in str(value):
        if char == "\n":
            dispatch_key_press(tab, runner, Keys.ENTER, modifiers)
        elif char == "\r":
            dispatch_key_press(tab, runner, Keys.RETURN, modifiers)
        else:
            dispatch_key_press(tab, runner, char, modifiers)


def dispatch_key_press(tab: Any, runner: Any, value: str, modifiers: int = 0) -> None:
    dispatch_key(tab, runner, value, "keyDown", modifiers)
    dispatch_key(tab, runner, value, "keyUp", modifiers)
