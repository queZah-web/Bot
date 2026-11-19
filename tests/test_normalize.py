from zhoo.core.normalize import normalize


def test_removes_tashkeel_and_tatweel():
    assert normalize("رَفْـــعُ  مُدِيـر") == "رفع مدير"


def test_unifies_letters():
    assert normalize("الأوامر") == normalize("الاوامر")
    assert normalize("مساعدة") == normalize("مساعده")
    assert normalize("أدمن") == normalize("ادمن")
    assert normalize("لگيت") == normalize("لكيت")


def test_invisible_chars_and_spaces():
    assert normalize("‏ايدي‏   ") == "ايدي"
    assert normalize("") == ""


def test_env_txt_fallback(tmp_path, monkeypatch):
    import zhoo.config as cfg
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("OWNER_ID", raising=False)
    monkeypatch.setattr(cfg, "ROOT", tmp_path)
    (tmp_path / "env.txt").write_text("BOT_TOKEN=123456:" + "A" * 35 + "\nOWNER_ID=8864617026\n", encoding="utf-8")
    s = cfg.load_settings()
    assert s.owner_id == 8864617026
