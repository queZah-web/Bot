from zhoo.core.ranks import Rank, RankDecision as D, check_rank_change, coerce_rank


def chk(actor, target, new, floor=Rank.MEMBER, self_=False):
    return check_rank_change(actor, target, floor, new, is_self=self_)


def test_owner_can_promote_manager():
    assert chk(Rank.OWNER, Rank.MEMBER, Rank.MANAGER) == D.OK


def test_cannot_grant_equal_or_higher():
    assert chk(Rank.MANAGER, Rank.MEMBER, Rank.MANAGER) == D.CANT_GRANT
    assert chk(Rank.MANAGER, Rank.MEMBER, Rank.OWNER) == D.CANT_GRANT


def test_cannot_touch_higher_or_equal():
    assert chk(Rank.MANAGER, Rank.MANAGER, Rank.MEMBER) == D.TARGET_HIGHER
    assert chk(Rank.MANAGER, Rank.OWNER, Rank.MEMBER) == D.TARGET_HIGHER


def test_self_and_protected():
    assert chk(Rank.OWNER, Rank.OWNER, Rank.MEMBER, self_=True) == D.SELF
    assert chk(Rank.DEVELOPER, Rank.CREATOR, Rank.MEMBER) == D.PROTECTED


def test_creator_and_developer_never_grantable():
    assert chk(Rank.DEVELOPER, Rank.MEMBER, Rank.CREATOR) == D.CANT_GRANT
    assert chk(Rank.DEVELOPER, Rank.MEMBER, Rank.OWNER) == D.OK


def test_same_and_floor():
    assert chk(Rank.OWNER, Rank.VIP, Rank.VIP) == D.SAME
    assert chk(Rank.OWNER, Rank.ADMIN, Rank.MEMBER, floor=Rank.ADMIN) == D.BELOW_FLOOR
    assert chk(Rank.OWNER, Rank.ADMIN, Rank.MANAGER, floor=Rank.ADMIN) == D.OK


def test_coerce_rejects_garbage():
    assert coerce_rank(999) == Rank.MEMBER
    assert coerce_rank(Rank.CREATOR) == Rank.MEMBER  # المنشئ ما ينخزن
    assert coerce_rank(Rank.MANAGER) == Rank.MANAGER
