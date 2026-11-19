from zhoo.core.ranks import Rank
from zhoo.repositories.audit import AuditRepo
from zhoo.repositories.bot_settings import BotSettingsRepo
from zhoo.repositories.groups import GroupsRepo
from zhoo.repositories.members import MembersRepo
from zhoo.repositories.users import UsersRepo


async def test_migrations_idempotent(db):
    await db._migrate()
    assert await db.fetchval("SELECT COUNT(*) FROM schema_version") == 1


async def test_username_moves_to_new_owner(db):
    users = UsersRepo(db)
    await users.upsert(1, "A", None, "Zed", False)
    await users.upsert(2, "B", None, "zed", False)
    assert (await users.find_by_username("@ZED")).user_id == 2
    assert (await users.get(1)).username is None


async def test_ranks_isolated_per_group(db):
    groups, members = GroupsRepo(db), MembersRepo(db)
    await groups.upsert(-100, "G1", None)
    await groups.upsert(-200, "G2", None)
    prev = await members.set_rank(-100, 5, Rank.MANAGER, 1)
    assert prev == Rank.MEMBER
    assert await members.get_rank(-100, 5) == Rank.MANAGER
    assert await members.get_rank(-200, 5) == Rank.MEMBER
    assert await members.set_rank(-100, 5, Rank.VIP, 1) == Rank.MANAGER


async def test_message_counts_skip_unknown_groups(db):
    groups, members = GroupsRepo(db), MembersRepo(db)
    await groups.upsert(-100, "G1", None)
    await members.add_message_counts([(-100, 7, 3, 1), (-999, 7, 3, 1)])
    await members.add_message_counts([(-100, 7, 2, 2)])
    assert await members.message_count(-100, 7) == 5
    assert await members.message_count(-999, 7) == 0


async def test_group_migration_moves_everything(db):
    groups, members, audit = GroupsRepo(db), MembersRepo(db), AuditRepo(db)
    await groups.upsert(-1, "old", None)
    await members.set_rank(-1, 5, Rank.OWNER, 1)
    await audit.log("x", chat_id=-1)
    await groups.migrate_chat_id(-1, -1001)
    assert await members.get_rank(-1001, 5) == Rank.OWNER
    assert await groups.count_all() == 1
    assert len(await audit.recent(chat_id=-1001)) == 1


async def test_bot_settings_cache(db):
    s = BotSettingsRepo(db)
    await s.load()
    assert not s.get_bool("maintenance")
    await s.set("maintenance", "1")
    s2 = BotSettingsRepo(db)
    await s2.load()
    assert s2.get_bool("maintenance")
