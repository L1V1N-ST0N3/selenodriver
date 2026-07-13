from __future__ import annotations

import json
import os
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
        self.extension_files: list[str] = []
        self.startup_preferences_error: str | None = None

    def add_argument(self, argument: str) -> None:
        self.arguments.append(argument)

    def add_arguments(self, *arguments: str) -> None:
        for argument in arguments:
            self.add_argument(argument)

    def add_experimental_option(self, name: str, value: Any) -> None:
        self.experimental_options[name] = value

    def add_extension(self, path: str | Path) -> None:
        """Record a Selenium-style extension path for compatibility.

        nodriver cannot install packed CRX files through ChromeOptions. Paths
        remain visible in ``capabilities`` while unpacked extensions should be
        supplied through a browser argument or a selenodriver extension hook.
        """
        self.extension_files.append(str(path))

    def add_encoded_extension(self, extension: str) -> None:
        self.extension_files.append(str(extension))

    def to_capabilities(self) -> dict[str, Any]:
        return self.capabilities

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

    def apply_profile_preferences(self) -> bool:
        """Atomically merge dotted Chrome prefs before the browser starts."""
        prefs = self.experimental_options.get("prefs")
        user_data_dir = self.to_nodriver_kwargs().get("user_data_dir")
        if not isinstance(prefs, dict) or not user_data_dir:
            return False
        target = Path(user_data_dir) / "Default" / "Preferences"
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
            if not isinstance(data, dict):
                data = {}
            for dotted_key, value in prefs.items():
                current = data
                parts = str(dotted_key).split(".")
                for part in parts[:-1]:
                    child = current.get(part)
                    if not isinstance(child, dict):
                        child = {}
                        current[part] = child
                    current = child
                current[parts[-1]] = value
            temporary = target.with_name(target.name + ".selenodriver.tmp")
            temporary.write_text(
                json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(temporary, target)
            self.startup_preferences_error = None
            return True
        except Exception as error:
            self.startup_preferences_error = str(error)
            return False

    @property
    def capabilities(self) -> dict[str, Any]:
        capabilities = dict(self.experimental_options.get("capabilities", {}))
        capabilities["browserName"] = "chrome"
        capabilities["goog:chromeOptions"] = {
            "args": list(self.arguments),
            "binary": self.binary_location,
            "extensions": list(self.extension_files),
            "experimentalOptions": dict(self.experimental_options),
        }
        return capabilities


ChromeOptions = Options
