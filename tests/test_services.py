import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy import update as sqla_update

from services.auth_service import AuthService
from services.link_service import LinkService
from services.base import BaseService
from models import User, Link

class TestBaseService:
    def test_session_attribute_is_set_on_init(self):
        svc = BaseService()
        from database import async_session_maker
        assert svc.session is async_session_maker

class TestAuthServiceRegister:
    async def test_register_returns_user_object(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = AuthService()
            user = await svc.register("new@example.com", "pass1234")
        assert user.email == "new@example.com"
        assert user.id is not None

    async def test_register_hashes_password(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = AuthService()
            user = await svc.register("hash@example.com", "plaintext")
        assert user.hashed_password != "plaintext"
        assert user.hashed_password.startswith("$2")

    async def test_register_duplicate_email_raises_value_error(
        self, session_maker_factory
    ):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = AuthService()
            await svc.register("dup@example.com", "pass")
            with pytest.raises(ValueError, match="email already registered"):
                await svc.register("dup@example.com", "other")


class TestAuthServiceLogin:
    async def test_login_returns_jwt_string(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = AuthService()
            await svc.register("login@example.com", "mypass")
            token = await svc.login("login@example.com", "mypass")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    async def test_login_wrong_password_raises(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = AuthService()
            await svc.register("wrong@example.com", "correct")
            with pytest.raises(ValueError, match="incorrect email or password"):
                await svc.login("wrong@example.com", "incorrect")

    async def test_login_unknown_user_raises(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = AuthService()
            with pytest.raises(ValueError, match="incorrect email or password"):
                await svc.login("ghost@example.com", "pass")


class TestAuthServiceGetUser:
    async def test_get_user_by_email_found(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = AuthService()
            await svc.register("find@example.com", "pass")
            user = await svc.get_user_by_email("find@example.com")
        assert user is not None
        assert user.email == "find@example.com"

    async def test_get_user_by_email_not_found(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = AuthService()
            result = await svc.get_user_by_email("nobody@example.com")
        assert result is None

class TestLinkServiceCreate:
    async def test_create_with_custom_alias(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            link = await svc.create_link(
                original_url="https://aliased.com",
                custom_alias="myalias_svc",
                expires_at=datetime.now() + timedelta(days=1),
            )
        assert link.short_code == "myalias_svc"
        assert link.custom_alias == "myalias_svc"

    async def test_create_generates_unique_short_code(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            link = await svc.create_link(
                original_url="https://generated.com",
                expires_at=datetime.now() + timedelta(days=1),
            )
        assert link.short_code is not None
        assert len(link.short_code) == 6

    async def test_create_duplicate_alias_raises(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await svc.create_link(
                original_url="https://first.com",
                custom_alias="taken_alias",
                expires_at=datetime.now() + timedelta(days=1),
            )
            with pytest.raises(ValueError, match="Alias already in use"):
                await svc.create_link(
                    original_url="https://second.com",
                    custom_alias="taken_alias",
                    expires_at=datetime.now() + timedelta(days=1),
                )

    async def test_create_with_user(self, session_maker_factory):
        mock_user = MagicMock(spec=User)
        mock_user.id = 100
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            link = await svc.create_link(
                original_url="https://owned.com",
                user=mock_user,
                expires_at=datetime.now() + timedelta(days=1),
            )
        assert link.user_id == 100

    async def test_create_documents_timedelta_bug(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            with patch("services.link_service.settings") as mock_settings:
                mock_settings.DEFAULT_LINK_EXPIRE_DAYS = 30
                svc = LinkService()
                with pytest.raises(NameError):
                    await svc.create_link(original_url="https://bug.com")


class TestLinkServiceGetAndRecord:
    async def test_get_by_short_code_found(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await svc.create_link(
                original_url="https://findme.com",
                custom_alias="find_sc",
                expires_at=datetime.now() + timedelta(days=1),
            )
            found = await svc.get_by_short_code("find_sc")
        assert found is not None and found.short_code == "find_sc"

    async def test_get_by_short_code_not_found(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            assert await svc.get_by_short_code("no_such_code") is None

    async def test_get_stats_returns_link(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await svc.create_link(
                original_url="https://stats.com",
                custom_alias="stats_sc",
                expires_at=datetime.now() + timedelta(days=1),
            )
            stats = await svc.get_stats("stats_sc")
        assert stats is not None

    async def test_record_click_increments_count(self, session_maker_factory):
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            link = await svc.create_link(
                original_url="https://click.com",
                custom_alias="click_sc",
                expires_at=datetime.now() + timedelta(days=1),
            )
            before = link.click_count
            await svc.record_click(link)
        assert link.click_count == before + 1


class TestLinkServiceUpdate:
    async def _create_owned_link(self, svc, factory, alias, owner_id):
        link = await svc.create_link(
            original_url="https://owned.com",
            custom_alias=alias,
            expires_at=datetime.now() + timedelta(days=1),
        )
        async with factory() as session:
            await session.execute(
                sqla_update(Link)
                .where(Link.short_code == alias)
                .values(user_id=owner_id)
            )
            await session.commit()
        return link

    async def test_update_by_owner_succeeds(self, session_maker_factory):
        user = MagicMock(spec=User)
        user.id = 5
        user.is_superuser = False
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await self._create_owned_link(svc, session_maker_factory, "upd_sc", 5)
            updated = await svc.update_link("upd_sc", "https://updated.com", user)
        assert updated.original_url == "https://updated.com"

    async def test_update_by_superuser_succeeds(self, session_maker_factory):
        superuser = MagicMock(spec=User)
        superuser.id = 99
        superuser.is_superuser = True
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await self._create_owned_link(svc, session_maker_factory, "super_sc", 1)
            updated = await svc.update_link("super_sc", "https://super.com", superuser)
        assert updated.original_url == "https://super.com"

    async def test_update_nonexistent_link_raises(self, session_maker_factory):
        user = MagicMock(spec=User)
        user.id = 1
        user.is_superuser = False
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            with pytest.raises(ValueError, match="link not found"):
                await svc.update_link("no_link", "https://x.com", user)

    async def test_update_by_other_user_raises(self, session_maker_factory):
        other = MagicMock(spec=User)
        other.id = 999
        other.is_superuser = False
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await self._create_owned_link(svc, session_maker_factory, "auth_sc", 1)
            with pytest.raises(ValueError, match="not authorized"):
                await svc.update_link("auth_sc", "https://hacked.com", other)


class TestLinkServiceDelete:
    async def _create_owned_link(self, svc, factory, alias, owner_id):
        await svc.create_link(
            original_url="https://del.com",
            custom_alias=alias,
            expires_at=datetime.now() + timedelta(days=1),
        )
        async with factory() as session:
            await session.execute(
                sqla_update(Link)
                .where(Link.short_code == alias)
                .values(user_id=owner_id)
            )
            await session.commit()

    async def test_delete_by_owner_succeeds(self, session_maker_factory):
        user = MagicMock(spec=User)
        user.id = 6
        user.is_superuser = False
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await self._create_owned_link(svc, session_maker_factory, "del_sc", 6)
            await svc.delete_link("del_sc", user)
            assert await svc.get_by_short_code("del_sc") is None

    async def test_delete_nonexistent_raises(self, session_maker_factory):
        user = MagicMock(spec=User)
        user.id = 1
        user.is_superuser = False
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            with pytest.raises(ValueError, match="link not found"):
                await svc.delete_link("ghost_del", user)

    async def test_delete_by_other_user_raises(self, session_maker_factory):
        other = MagicMock(spec=User)
        other.id = 555
        other.is_superuser = False
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await self._create_owned_link(
                svc, session_maker_factory, "del_auth_sc", 1
            )
            with pytest.raises(ValueError, match="not authorized"):
                await svc.delete_link("del_auth_sc", other)


class TestLinkServiceQuery:
    async def test_search_by_url(self, session_maker_factory):
        url = "https://searchable.com"
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await svc.create_link(
                original_url=url,
                custom_alias="srch1",
                expires_at=datetime.now() + timedelta(days=1),
            )
            results = await svc.search_by_url(url)
        assert len(results) >= 1
        assert all(lnk.original_url == url for lnk in results)

    async def test_get_user_links(self, session_maker_factory):
        user = MagicMock(spec=User)
        user.id = 55
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            for i in range(3):
                lnk_alias = f"ulnk_{i}_55"
                await svc.create_link(
                    original_url=f"https://user{i}.com",
                    custom_alias=lnk_alias,
                    expires_at=datetime.now() + timedelta(days=1),
                )
                async with session_maker_factory() as session:
                    await session.execute(
                        sqla_update(Link)
                        .where(Link.short_code == lnk_alias)
                        .values(user_id=55)
                    )
                    await session.commit()
            links = await svc.get_user_links(user)
        assert len(links) == 3

    async def test_get_project_links(self, session_maker_factory):
        user = MagicMock(spec=User)
        user.id = 60
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            for i in range(2):
                lnk_alias = f"proj_{i}_60"
                await svc.create_link(
                    original_url=f"https://proj{i}.com",
                    custom_alias=lnk_alias,
                    project="myproj",
                    expires_at=datetime.now() + timedelta(days=1),
                )
                async with session_maker_factory() as session:
                    await session.execute(
                        sqla_update(Link)
                        .where(Link.short_code == lnk_alias)
                        .values(user_id=60)
                    )
                    await session.commit()
            links = await svc.get_project_links("myproj", user)
        assert len(links) == 2

    async def test_get_expired_links(self, session_maker_factory):
        user = MagicMock(spec=User)
        user.id = 70
        past = datetime.now() - timedelta(hours=2)
        with patch("services.base.async_session_maker", session_maker_factory):
            svc = LinkService()
            await svc.create_link(
                original_url="https://expired.com",
                custom_alias="exp_svc",
                expires_at=past,
            )
            async with session_maker_factory() as session:
                await session.execute(
                    sqla_update(Link)
                    .where(Link.short_code == "exp_svc")
                    .values(user_id=70)
                )
                await session.commit()
            links = await svc.get_expired_links(user)
        assert any(lnk.short_code == "exp_svc" for lnk in links)
