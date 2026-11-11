from __future__ import annotations

from typing import Any


def install_cdp_event_compatibility() -> None:
    """Tolerate optional Page event fields omitted by newer Chrome builds."""
    from nodriver import cdp

    dialog_event = cdp.page.JavascriptDialogOpening
    if not getattr(dialog_event, "_selenodriver_optional_fields_patch", False):

        def dialog_from_json(cls: type[Any], payload: dict[str, Any]) -> Any:
            frame_id = payload.get("frameId")
            return cls(
                url=str(payload.get("url", "")),
                frame_id=(
                    cdp.page.FrameId.from_json(frame_id)
                    if frame_id is not None
                    else None
                ),
                message=str(payload.get("message", "")),
                type_=cdp.page.DialogType.from_json(payload.get("type", "alert")),
                has_browser_handler=bool(payload.get("hasBrowserHandler", False)),
                default_prompt=(
                    str(payload["defaultPrompt"])
                    if payload.get("defaultPrompt") is not None
                    else None
                ),
            )

        dialog_event.from_json = classmethod(dialog_from_json)
        dialog_event._selenodriver_optional_fields_patch = True

    navigation_event = cdp.page.NavigatedWithinDocument
    if not getattr(navigation_event, "_selenodriver_optional_fields_patch", False):

        def navigation_from_json(cls: type[Any], payload: dict[str, Any]) -> Any:
            return cls(
                frame_id=cdp.page.FrameId.from_json(payload["frameId"]),
                url=str(payload.get("url", "")),
                navigation_type=str(payload.get("navigationType", "unknown")),
            )

        navigation_event.from_json = classmethod(navigation_from_json)
        navigation_event._selenodriver_optional_fields_patch = True
