import pytest

from zhoo.core.commands import CommandRegistry
from zhoo.core.ranks import Rank


async def _h(cx):
    pass


@pytest.fixture
def reg():
    r = CommandRegistry()
    r.command("id", ("ايدي",), section="g", description="", args="target")(_h)
    r.command("zhoo", ("زهو",), section="g", description="")(_h)
    r.command("pm", ("رفع مدير",), section="r", description="", args="target")(_h)
    r.command("pgm", ("رفع مدير عام",), section="r", description="", args="target")(_h)
    r.command("say", ("قول",), section="g", description="", args="text")(_h)
    return r


def test_exact(reg):
    assert reg.parse("ايدي").command.key == "id"
    assert reg.parse("زهو").command.key == "zhoo"


def test_longest_match(reg):
    assert reg.parse("رفع مدير عام").command.key == "pgm"
    assert reg.parse("رفع مدير").command.key == "pm"
    p = reg.parse("رفع مدير عام @someone")
    assert p.command.key == "pgm" and p.args == ["@someone"]


def test_variants(reg):
    assert reg.parse("رَفع  مديـر 123456789").command.key == "pm"


def test_sentence_is_not_command(reg):
    assert reg.parse("زهو شلونك") is None
    assert reg.parse("ايدي حلو") is None
    assert reg.parse("شنو ايدي") is None
    assert reg.parse("رفع مدير احمد") is None


def test_target_args(reg):
    assert reg.parse("ايدي @user_name").args == ["@user_name"]
    assert reg.parse("ايدي 123456").args == ["123456"]
    assert reg.parse("ايدي احمد", has_text_mention=True) is not None


def test_text_args_keep_original(reg):
    p = reg.parse("قول  هلا\nبيكم")
    assert p.raw_args == "هلا\nبيكم"


def test_duplicate_name_rejected(reg):
    with pytest.raises(ValueError):
        reg.command("x", ("ايدي",), section="g", description="")(_h)


def test_default_rank(reg):
    assert reg.get("id").min_rank == Rank.MEMBER
