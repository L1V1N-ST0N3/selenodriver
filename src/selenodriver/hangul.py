from __future__ import annotations

import unicodedata
from typing import Iterator


# Unicode Hangul syllables are algorithmically composed from these blocks.
CHOSEONG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNGSEONG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONGSEONG = "-ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"

COMPOUND_JAMO = {
    "ㅘ": "ㅗㅏ",
    "ㅙ": "ㅗㅐ",
    "ㅚ": "ㅗㅣ",
    "ㅝ": "ㅜㅓ",
    "ㅞ": "ㅜㅔ",
    "ㅟ": "ㅜㅣ",
    "ㅢ": "ㅡㅣ",
    "ㄳ": "ㄱㅅ",
    "ㄵ": "ㄴㅈ",
    "ㄶ": "ㄴㅎ",
    "ㄺ": "ㄹㄱ",
    "ㄻ": "ㄹㅁ",
    "ㄼ": "ㄹㅂ",
    "ㄽ": "ㄹㅅ",
    "ㄾ": "ㄹㅌ",
    "ㄿ": "ㄹㅍ",
    "ㅀ": "ㄹㅎ",
    "ㅄ": "ㅂㅅ",
}

DOUBEOLSIK = {
    "ㅂ": "q", "ㅈ": "w", "ㄷ": "e", "ㄱ": "r", "ㅅ": "t",
    "ㅛ": "y", "ㅕ": "u", "ㅑ": "i", "ㅐ": "o", "ㅔ": "p",
    "ㅁ": "a", "ㄴ": "s", "ㅇ": "d", "ㄹ": "f", "ㅎ": "g",
    "ㅗ": "h", "ㅓ": "j", "ㅏ": "k", "ㅣ": "l", "ㅋ": "z",
    "ㅌ": "x", "ㅊ": "c", "ㅍ": "v", "ㅠ": "b", "ㅜ": "n",
    "ㅡ": "m", "ㅃ": "Q", "ㅉ": "W", "ㄸ": "E", "ㄲ": "R",
    "ㅆ": "T", "ㅒ": "O", "ㅖ": "P",
}


def is_hangul_syllable(char: str) -> bool:
    return len(char) == 1 and 0xAC00 <= ord(char) <= 0xD7A3


def is_hangul_jamo(char: str) -> bool:
    return len(char) == 1 and (char in DOUBEOLSIK or 0x1100 <= ord(char) <= 0x11FF or 0x3130 <= ord(char) <= 0x318F)


def is_hangul_text(text: str) -> bool:
    return any(is_hangul_syllable(char) or is_hangul_jamo(char) for char in text)


def _decompose_syllable(char: str) -> str:
    index = ord(char) - 0xAC00
    lead = index // (21 * 28)
    vowel = (index % (21 * 28)) // 28
    tail = index % 28
    result = CHOSEONG[lead] + JUNGSEONG[vowel]
    if tail:
        result += JONGSEONG[tail]
    return result


def decompose(text: str, *, expand_compounds: bool = True) -> str:
    result: list[str] = []
    for char in str(text):
        value = _decompose_syllable(char) if is_hangul_syllable(char) else char
        if expand_compounds:
            for item in value:
                result.append(COMPOUND_JAMO.get(item, item))
        else:
            result.append(value)
    return "".join(result)


def split_hangul_runs(text: str) -> Iterator[tuple[bool, str]]:
    """Yield (is_hangul, text) runs without losing non-Hangul characters."""
    buffer: list[str] = []
    current: bool | None = None
    for char in str(text):
        is_hangul = is_hangul_syllable(char) or is_hangul_jamo(char)
        if current is not None and is_hangul != current:
            yield current, "".join(buffer)
            buffer.clear()
        current = is_hangul
        buffer.append(char)
    if buffer:
        yield bool(current), "".join(buffer)


def iter_graphemes(text: str) -> Iterator[str]:
    """Yield practical grapheme clusters without an external regex package."""
    chars = list(str(text))
    index = 0
    while index < len(chars):
        cluster = [chars[index]]
        index += 1
        while index < len(chars):
            char = chars[index]
            codepoint = ord(char)
            is_extend = (
                unicodedata.combining(char) != 0
                or 0xFE00 <= codepoint <= 0xFE0F
                or 0x1F3FB <= codepoint <= 0x1F3FF
            )
            if is_extend:
                cluster.append(char)
                index += 1
                continue
            if char == "\u200d" and index + 1 < len(chars):
                cluster.extend((char, chars[index + 1]))
                index += 2
                continue
            break
        yield "".join(cluster)


def split_input_runs(text: str) -> Iterator[tuple[str, str]]:
    """Split text into key, Hangul, and completed-Unicode input runs."""
    current_kind: str | None = None
    buffer: list[str] = []
    for cluster in iter_graphemes(text):
        if is_hangul_text(cluster):
            kind = "hangul"
        elif all(ord(char) < 128 for char in cluster):
            kind = "key"
        else:
            kind = "text"
        if current_kind is not None and kind != current_kind:
            yield current_kind, "".join(buffer)
            buffer.clear()
        current_kind = kind
        buffer.append(cluster)
    if buffer:
        yield current_kind or "text", "".join(buffer)


def to_dubeolsik(text: str) -> str:
    """Convert Hangul syllables to 2-beolsik keystrokes without external packages."""
    return "".join(DOUBEOLSIK.get(char, char) for char in decompose(text))
