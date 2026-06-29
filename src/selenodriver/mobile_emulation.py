from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class MobileProfile:
    name: str
    user_agent: str
    platform: str
    width: int
    height: int
    device_scale_factor: float
    os_type: str | None = None
    max_touch_points: int = 5
    locale: str | None = None
    languages: list[str] | None = None
    timezone_id: str | None = None
    orientation: Literal["portrait", "landscape"] = "portrait"
    user_agent_metadata: dict[str, Any] | None = None
    extra_scripts: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "MobileProfile":
        language = data.get("language") or data.get("locale")
        languages = data.get("languages")
        return cls(
            name=data.get("name") or data.get("device_name") or "Custom Mobile Device",
            os_type=data.get("os_type"),
            user_agent=data.get("user_agent") or data.get("UA") or data.get("ua"),
            platform=data.get("platform") or ("iPhone" if data.get("os_type") == "ios" else "Android"),
            width=int(data["width"]),
            height=int(data["height"]),
            device_scale_factor=float(data.get("device_scale_factor", data.get("devicePixelRatio", 1))),
            max_touch_points=int(data.get("max_touch_points", data.get("maxTouchPoints", 5))),
            locale=language,
            languages=list(languages) if languages else ([language] if language else None),
            timezone_id=data.get("timezone_id") or data.get("timezone"),
            orientation=data.get("orientation", "portrait"),
            user_agent_metadata=data.get("user_agent_metadata") or data.get("userAgentData"),
            extra_scripts=list(data.get("extra_scripts", [])),
        )


ANDROID_PROFILES = [
    MobileProfile(
        name="Pixel 7",
        user_agent=(
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Mobile Safari/537.36"
        ),
        platform="Android",
        width=412,
        height=915,
        device_scale_factor=2.625,
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        user_agent_metadata={
            "platform": "Android",
            "platformVersion": "13",
            "architecture": "",
            "model": "Pixel 7",
            "mobile": True,
            "brands": [
                {"brand": "Chromium", "version": "120"},
                {"brand": "Google Chrome", "version": "120"},
            ],
            "fullVersionList": [
                {"brand": "Chromium", "version": "120.0.0.0"},
                {"brand": "Google Chrome", "version": "120.0.0.0"},
            ],
        },
    ),
    MobileProfile(
        name="Galaxy S23",
        user_agent=(
            "Mozilla/5.0 (Linux; Android 14; SM-S911B) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Mobile Safari/537.36"
        ),
        platform="Android",
        width=360,
        height=780,
        device_scale_factor=3,
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        user_agent_metadata={
            "platform": "Android",
            "platformVersion": "14",
            "architecture": "",
            "model": "SM-S911B",
            "mobile": True,
            "brands": [
                {"brand": "Chromium", "version": "121"},
                {"brand": "Google Chrome", "version": "121"},
            ],
            "fullVersionList": [
                {"brand": "Chromium", "version": "121.0.0.0"},
                {"brand": "Google Chrome", "version": "121.0.0.0"},
            ],
        },
    ),
]


IOS_PROFILES = [
    MobileProfile(
        name="iPhone 14",
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/16.6 Mobile/15E148 Safari/604.1"
        ),
        platform="iPhone",
        width=390,
        height=844,
        device_scale_factor=3,
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        user_agent_metadata=None,
    ),
    MobileProfile(
        name="iPhone 15 Pro",
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        ),
        platform="iPhone",
        width=393,
        height=852,
        device_scale_factor=3,
        locale="ko-KR",
        timezone_id="Asia/Seoul",
        user_agent_metadata=None,
    ),
]


class MobileEmulationExtension:
    def __init__(
        self,
        profile: str | dict[str, Any] | MobileProfile = "android",
        *,
        seed: int | None = None,
        apply_on_attach: bool = True,
    ):
        self.profile = self._resolve_profile(profile, seed)
        self.apply_on_attach = apply_on_attach
        self.init_script_ids: list[Any] = []

    def on_attach(self, driver: Any) -> None:
        if self.apply_on_attach:
            self.apply(driver)

    def before_navigate(self, driver: Any, _url: str) -> None:
        self.apply(driver)

    def after_navigate(self, driver: Any, _url: str) -> None:
        self.apply(driver)

    def on_context_changed(self, driver: Any) -> None:
        self.apply(driver)

    def before_quit(self, _driver: Any) -> None:
        self.init_script_ids.clear()

    def on_new_tab(self, driver: Any, _tab: Any, _handle: str) -> None:
        self.apply(driver)

    def apply(self, driver: Any) -> None:
        from nodriver import cdp

        metadata = self._build_user_agent_metadata()
        driver.send_cdp(
            cdp.emulation.set_user_agent_override(
                self.profile.user_agent,
                accept_language=self._accept_language(),
                platform=self.profile.platform,
                user_agent_metadata=metadata,
            )
        )
        driver.send_cdp(
            cdp.emulation.set_device_metrics_override(
                width=self.profile.width,
                height=self.profile.height,
                device_scale_factor=self.profile.device_scale_factor,
                mobile=True,
                screen_width=self.profile.width,
                screen_height=self.profile.height,
                screen_orientation=cdp.emulation.ScreenOrientation(
                    "portraitPrimary" if self.profile.orientation == "portrait" else "landscapePrimary",
                    0 if self.profile.orientation == "portrait" else 90,
                ),
            )
        )
        driver.send_cdp(
            cdp.emulation.set_touch_emulation_enabled(
                True,
                max_touch_points=self.profile.max_touch_points,
            )
        )
        if self.profile.locale:
            driver.send_cdp(cdp.emulation.set_locale_override(self.profile.locale))
        if self.profile.timezone_id:
            driver.send_cdp(cdp.emulation.set_timezone_override(self.profile.timezone_id))
        for script in self.profile.extra_scripts:
            script_id = driver.add_init_script(script, run_immediately=True)
            self.init_script_ids.append(script_id)

    def _build_user_agent_metadata(self):
        if not self.profile.user_agent_metadata:
            return None
        from nodriver import cdp

        data = self.profile.user_agent_metadata
        return cdp.emulation.UserAgentMetadata(
            platform=data.get("platform", self.profile.platform),
            platform_version=data.get("platformVersion", ""),
            architecture=data.get("architecture", ""),
            model=data.get("model", ""),
            mobile=bool(data.get("mobile", True)),
            brands=[
                cdp.emulation.UserAgentBrandVersion(item["brand"], item["version"])
                for item in data.get("brands", [])
            ],
            full_version_list=[
                cdp.emulation.UserAgentBrandVersion(item["brand"], item["version"])
                for item in data.get("fullVersionList", [])
            ],
            full_version=data.get("uaFullVersion"),
            bitness=data.get("bitness"),
            wow64=data.get("wow64"),
        )

    def _resolve_profile(self, profile: str | dict[str, Any] | MobileProfile, seed: int | None) -> MobileProfile:
        if isinstance(profile, MobileProfile):
            return profile
        if isinstance(profile, dict):
            return MobileProfile.from_mapping(profile)
        rng = random.Random(seed)
        key = profile.lower()
        if key == "android":
            return rng.choice(ANDROID_PROFILES)
        if key in {"ios", "iphone"}:
            return rng.choice(IOS_PROFILES)
        raise ValueError("profile must be 'android', 'ios', a dict, or MobileProfile")

    def _accept_language(self) -> str | None:
        if self.profile.languages:
            return ",".join(self.profile.languages)
        return self.profile.locale
