import pytest
from datetime import datetime, timedelta
from sqlalchemy import update as sqla_update

from repositories.base import BaseRepository
from repositories.link_repository import LinkRepository
from repositories.user_repository import UserRepository
from models import Link, User

class TestBaseRepository:
    def test_stores_session_reference(self):
        sentinel = object()
        repo = BaseRepository(sentinel)
        assert repo.db is sentinel

class TestUserRepository:
    async def test_create_returns_user_with_id(self, db_session):
        repo = UserRepository(db_session)
        user = await repo.create("alice@example.com", "hashed_pw")
        assert user.id is not None
        assert user.email == "alice@example.com"
        assert user.hashed_password == "hashed_pw"

    async def test_create_sets_is_active_true_by_default(self, db_session):
        repo = UserRepository(db_session)
        user = await repo.create("bob@example.com", "hash")
        assert user.is_active is True

    async def test_get_by_email_finds_existing_user(self, db_session):
        repo = UserRepository(db_session)
        await repo.create("carol@example.com", "hash")
        found = await repo.get_by_email("carol@example.com")
        assert found is not None
        assert found.email == "carol@example.com"

    async def test_get_by_email_returns_none_for_unknown(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.get_by_email("nobody@example.com") is None

    async def test_get_by_id_finds_existing_user(self, db_session):
        repo = UserRepository(db_session)
        user = await repo.create("dave@example.com", "hash")
        found = await repo.get_by_id(user.id)
        assert found is not None
        assert found.id == user.id

    async def test_get_by_id_returns_none_for_unknown(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.get_by_id(99999) is None

class TestLinkRepositoryCreate:
    async def test_create_minimal_link(self, db_session):
        repo = LinkRepository(db_session)
        link = await repo.create("abc123", "https://example.com")
        assert link.id is not None
        assert link.short_code == "abc123"
        assert link.original_url == "https://example.com"

    async def test_create_with_custom_alias(self, db_session):
        repo = LinkRepository(db_session)
        link = await repo.create(
            "myalias", "https://alias.com", custom_alias="myalias"
        )
        assert link.custom_alias == "myalias"

    async def test_create_with_user_id_and_project(self, db_session):
        repo = LinkRepository(db_session)
        link = await repo.create(
            "sc1", "https://proj.com", user_id=7, project="marketing"
        )
        assert link.user_id == 7
        assert link.project == "marketing"

    async def test_create_with_expiry(self, db_session):
        repo = LinkRepository(db_session)
        expires = datetime.now() + timedelta(days=10)
        link = await repo.create("exp1", "https://exp.com", expires_at=expires)
        assert link.expires_at is not None

    async def test_click_count_defaults_to_zero(self, db_session):
        repo = LinkRepository(db_session)
        link = await repo.create("zero", "https://zero.com")
        assert link.click_count == 0

class TestLinkRepositoryRead:
    async def test_get_by_short_code_found(self, db_session):
        repo = LinkRepository(db_session)
        await repo.create("findme", "https://find.com")
        link = await repo.get_by_short_code("findme")
        assert link is not None
        assert link.short_code == "findme"

    async def test_get_by_short_code_not_found(self, db_session):
        repo = LinkRepository(db_session)
        assert await repo.get_by_short_code("ghost") is None

    async def test_get_by_custom_alias_found(self, db_session):
        repo = LinkRepository(db_session)
        await repo.create("sc_al", "https://alias.com", custom_alias="thealias")
        link = await repo.get_by_custom_alias("thealias")
        assert link is not None
        assert link.custom_alias == "thealias"

    async def test_get_by_custom_alias_not_found(self, db_session):
        repo = LinkRepository(db_session)
        assert await repo.get_by_custom_alias("missing") is None

    async def test_get_by_original_url_returns_all_matches(self, db_session):
        repo = LinkRepository(db_session)
        url = "https://duplicate.com"
        await repo.create("dup1", url)
        await repo.create("dup2", url)
        results = await repo.get_by_original_url(url)
        assert len(results) == 2
        assert all(lnk.original_url == url for lnk in results)

    async def test_get_by_original_url_returns_empty_list(self, db_session):
        repo = LinkRepository(db_session)
        results = await repo.get_by_original_url("https://nothere.com")
        assert results == []

    async def test_get_by_user_returns_only_that_users_links(self, db_session):
        repo = LinkRepository(db_session)
        await repo.create("u10_1", "https://a.com", user_id=10)
        await repo.create("u10_2", "https://b.com", user_id=10)
        await repo.create("u20_1", "https://c.com", user_id=20)
        results = await repo.get_by_user(10)
        assert len(results) == 2
        assert all(lnk.user_id == 10 for lnk in results)

    async def test_get_by_project(self, db_session):
        repo = LinkRepository(db_session)
        await repo.create("p1l1", "https://a.com", project="alpha", user_id=1)
        await repo.create("p1l2", "https://b.com", project="alpha", user_id=1)
        await repo.create("p2l1", "https://c.com", project="beta",  user_id=1)
        results = await repo.get_by_project("alpha", 1)
        assert len(results) == 2
        assert all(lnk.project == "alpha" for lnk in results)


class TestLinkRepositoryWrite:
    async def test_update_changes_original_url(self, db_session):
        repo = LinkRepository(db_session)
        link = await repo.create("upd1", "https://old.com")
        link.original_url = "https://new.com"
        updated = await repo.update(link)
        assert updated.original_url == "https://new.com"

    async def test_delete_removes_link(self, db_session):
        repo = LinkRepository(db_session)
        link = await repo.create("del1", "https://delete.me")
        await repo.delete(link)
        assert await repo.get_by_short_code("del1") is None

    async def test_increment_click_increases_count(self, db_session):
        repo = LinkRepository(db_session)
        link = await repo.create("click1", "https://click.me")
        await repo.increment_click(link)
        assert link.click_count == 1

    async def test_increment_click_sets_last_used_at(self, db_session):
        repo = LinkRepository(db_session)
        link = await repo.create("click2", "https://used.me")
        assert link.last_used_at is None
        await repo.increment_click(link)
        assert link.last_used_at is not None

    async def test_increment_click_multiple_times(self, db_session):
        repo = LinkRepository(db_session)
        link = await repo.create("click3", "https://many.clicks")
        for _ in range(5):
            await repo.increment_click(link)
        assert link.click_count == 5


class TestLinkRepositoryExistsChecks:
    async def test_code_exists_true(self, db_session):
        repo = LinkRepository(db_session)
        await repo.create("exists1", "https://e.com")
        assert await repo.code_exists("exists1") is True

    async def test_code_exists_false(self, db_session):
        repo = LinkRepository(db_session)
        assert await repo.code_exists("notexists") is False

    async def test_alias_exists_via_custom_alias(self, db_session):
        repo = LinkRepository(db_session)
        await repo.create("sc_ae", "https://ae.com", custom_alias="aliasexists")
        assert await repo.alias_exists("aliasexists") is True

    async def test_alias_exists_via_short_code(self, db_session):
        repo = LinkRepository(db_session)
        await repo.create("codeonly", "https://co.com")
        assert await repo.alias_exists("codeonly") is True

    async def test_alias_does_not_exist(self, db_session):
        repo = LinkRepository(db_session)
        assert await repo.alias_exists("nothing_here") is False


class TestLinkRepositoryExpiredUnused:
    async def test_get_expired_returns_past_links(self, db_session):
        repo = LinkRepository(db_session)
        past   = datetime.now() - timedelta(hours=2)
        future = datetime.now() + timedelta(hours=2)
        await repo.create("exp_past",   "https://past.com",   expires_at=past)
        await repo.create("exp_future", "https://future.com", expires_at=future)
        await repo.create("no_expiry",  "https://no.com")
        expired = await repo.get_expired()
        codes = [lnk.short_code for lnk in expired]
        assert "exp_past"   in codes
        assert "exp_future" not in codes
        assert "no_expiry"  not in codes

    async def test_get_expired_filters_by_user_id(self, db_session):
        repo = LinkRepository(db_session)
        past = datetime.now() - timedelta(hours=1)
        await repo.create("u1_exp", "https://u1.com", expires_at=past, user_id=1)
        await repo.create("u2_exp", "https://u2.com", expires_at=past, user_id=2)
        only_user1 = await repo.get_expired(user_id=1)
        assert all(lnk.user_id == 1 for lnk in only_user1)
