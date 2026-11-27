import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zhoo.database.db import Database  # noqa: E402


@pytest.fixture
async def db():
    d = Database(":memory:")
    await d.connect()
    yield d
    await d.close()


@pytest.fixture(autouse=True)
def _open_chat_gate():
    """الاختبارات القديمة ترسل نفس السالفة ورا بعض؛ حد «رد كل 10 ثواني» يتفحص بـ test_zhoo_replies."""
    from zhoo.systems import extras, zhoo_replies
    extras._chat_source_limiter._hits.clear()
    zhoo_replies.gate.max_hits = 10 ** 6
    zhoo_replies.gate._hits.clear()
    yield
    zhoo_replies.gate.max_hits = 1
