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
