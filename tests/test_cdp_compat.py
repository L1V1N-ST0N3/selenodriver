from nodriver import cdp

from selenodriver.cdp_compat import install_cdp_event_compatibility


def test_dialog_event_accepts_missing_frame_id():
    event = cdp.util.parse_json_event(
        {
            "method": "Page.javascriptDialogOpening",
            "params": {
                "url": "https://m.pay.naver.com/",
                "message": "already agreed",
                "type": "alert",
                "hasBrowserHandler": True,
            },
        }
    )

    assert event.frame_id is None
    assert event.message == "already agreed"
    assert event.type_ == cdp.page.DialogType.ALERT


def test_dialog_event_preserves_frame_id_when_present():
    event = cdp.util.parse_json_event(
        {
            "method": "Page.javascriptDialogOpening",
            "params": {
                "url": "https://example.com/",
                "frameId": "frame-1",
                "message": "confirm",
                "type": "confirm",
                "hasBrowserHandler": True,
                "defaultPrompt": "value",
            },
        }
    )

    assert event.frame_id == "frame-1"
    assert event.default_prompt == "value"


def test_same_document_navigation_accepts_missing_navigation_type():
    event = cdp.util.parse_json_event(
        {
            "method": "Page.navigatedWithinDocument",
            "params": {
                "frameId": "frame-1",
                "url": "https://example.com/#next",
            },
        }
    )

    assert event.frame_id == "frame-1"
    assert event.navigation_type == "unknown"


def test_compatibility_installer_is_idempotent():
    before = cdp.page.JavascriptDialogOpening.from_json.__func__
    install_cdp_event_compatibility()
    after = cdp.page.JavascriptDialogOpening.from_json.__func__

    assert after is before
