"""The Streamlit app's password gate, run headless with Streamlit's AppTest (no browser, no model calls)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_password_gate_hides_the_app_until_the_right_password(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "open sesame")
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert [field.label for field in at.text_input] == ["Password"]
    assert len(at.chat_input) == 0

    at.text_input[0].input("wrong")
    at.button[0].click().run()
    assert "isn't right" in at.error[0].value
    assert len(at.chat_input) == 0

    at.text_input[0].input("open sesame")
    at.button[0].click().run()
    assert len(at.text_input) == 0
    assert len(at.chat_input) == 1 or "isn't set up" in at.error[0].value   # no index or keys on a CI machine


def test_no_password_set_means_no_gate(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert len(at.text_input) == 0
