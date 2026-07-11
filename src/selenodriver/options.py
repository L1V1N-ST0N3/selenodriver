from __future__ import annotations

from pathlib import Path
from typing import Any


class Options:
    def __init__(self):
        self.arguments: list[str] = []
        self.experimental_options: dict[str, Any] = {}
        self.binary_location: str | None = None
        self._headless: bool | None = None
        self._user_data_dir: str | None = None
        self._lang: str | None = None

    def add_argument(self, argument: str) -> None:
        self.arguments.append(argument)

    def add_arguments(self, *arguments: str) -> None:
        for argument in arguments:
            self.add_argument(argument)

    def add_experimental_option(self, name: str, value: Any) -> None:
        self.experimental_options[name] = value

    def set_capability(self, name: str, value: Any) -> None:
        self.experimental_options.setdefault("capabilities", {})[name] = value

    def set_headless(self, headless: bool = True) -> None:
        self._headless = bool(headless)

    def set_user_data_dir(self, path: str | Path) -> None:
        self._user_data_dir = str(path)

    @property
    def headless(self) -> bool | None:
        return self._headless

    @headless.setter
    def headless(self, value: bool) -> None:
        self._headless = bool(value)

    @property
    def lang(self) -> str | None:
        return self._lang

    @lang.setter
    def lang(self, value: str) -> None:
        self._lang = value

    def to_nodriver_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        browser_args: list[str] = []
        user_data_dir = self._user_data_dir
        for argument in self.arguments:
            if argument.startswith("--user-data-dir="):
                user_data_dir = argument.split("=", 1)[1]
            else:
                browser_args.append(argument)
        if browser_args:
            kwargs["browser_args"] = browser_args
        if self.binary_location:
            kwargs["browser_executable_path"] = self.binary_location
        if self._headless is not None:
            kwargs["headless"] = self._headless
        if user_data_dir is not None:
            kwargs["user_data_dir"] = user_data_dir
        if self._lang is not None:
            kwargs["lang"] = self._lang
        prefs = self.experimental_options.get("prefs")
        if prefs is not None:
            kwargs["prefs"] = prefs
        return kwargs

    @property
    def capabilities(self) -> dict[str, Any]:
        capabilities = dict(self.experimental_options.get("capabilities", {}))
        capabilities["browserName"] = "chrome"
        capabilities["goog:chromeOptions"] = {
            "args": list(self.arguments),
            "binary": self.binary_location,
            "experimentalOptions": dict(self.experimental_options),
        }
        return capabilities


ChromeOptions = Options
