import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from routes.links import (
    create_short_link,
    redirect_to_original,
    update_link,
    delete_link,
    get_link_stats,
    get_user_links,
    get_project_links,
    list_expired_links,
    build_short_url,
)
from models import User, Link
from schemas import LinkShortenResponse, LinkStats

def _mock_user(uid=1, email="user@example.com", superuser=False):
    u = MagicMock(spec=User)
    u.id = uid
    u.email = email
    u.is_active = True
    u.is_superuser = superuser
    return u


def _mock_link(
    short_code="abc123",
    original_url="https://example.com",
    user_id=1,
    expires_at=None,
    click_count=0,
    custom_alias=None,
    created_at=None,
    last_used_at=None,
):
    lnk = MagicMock(spec=Link)
    lnk.short_code = short_code
    lnk.original_url = original_url
    lnk.user_id = user_id
    lnk.expires_at = expires_at
    lnk.click_count = click_count
    lnk.custom_alias = custom_alias
    lnk.created_at = created_at or datetime(2024, 1, 1)
    lnk.last_used_at = last_used_at
    return lnk


def _mock_svc():
    return MagicMock()

def _mock_link_data(
    original_url="https://example.com",
    custom_alias=None,
    project="default",
    expires_at=None,
):
    ld = MagicMock()
    ld.original_url = original_url
    ld.custom_alias = custom_alias
    ld.project = project
    ld.expires_at = expires_at
    return ld

class TestBuildShortUrl:
    def test_returns_correct_path(self):
        assert build_short_url("abc123") == "/api/links/abc123"

    def test_different_codes(self):
        assert build_short_url("xyz") == "/api/links/xyz"

class TestCreateShortLink:
    async def test_success_returns_shorten_response(self):
        link = _mock_link("gen123", "https://example.com")
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.create_link = AsyncMock(return_value=link)
            result = await create_short_link(
                link_data=_mock_link_data(), user=None
            )
        assert isinstance(result, LinkShortenResponse)
        assert result.short_code == "gen123"
        assert result.short_url == "/api/links/gen123"
        assert result.original_url == "https://example.com"

    async def test_service_receives_correct_args(self):
        link = _mock_link("code1")
        user = _mock_user()
        expires = datetime.now() + timedelta(days=7)
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.create_link = AsyncMock(return_value=link)
            await create_short_link(
                link_data=_mock_link_data(
                    original_url="https://target.com",
                    custom_alias="mycode",
                    project="proj",
                    expires_at=expires,
                ),
                user=user,
            )
        call_kwargs = MockSvc.return_value.create_link.call_args.kwargs
        assert call_kwargs["original_url"] == "https://target.com"
        assert call_kwargs["custom_alias"] == "mycode"
        assert call_kwargs["user"] is user

    async def test_alias_in_use_raises_http_400(self):
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.create_link = AsyncMock(
                side_effect=ValueError("Alias already in use")
            )
            with pytest.raises(HTTPException) as exc:
                await create_short_link(link_data=_mock_link_data(), user=None)
        assert exc.value.status_code == 400
        assert "Alias already in use" in exc.value.detail

class TestRedirectToOriginal:
    async def test_cache_hit_sets_location_header(self):
        mock_resp = MagicMock()
        mock_resp.headers = {}
        with patch("routes.links.cache") as mock_cache:
            mock_cache.get = AsyncMock(
                return_value={"original_url": "https://cached.com"}
            )
            result = await redirect_to_original("abc123", mock_resp)
        assert mock_resp.headers["Location"] == "https://cached.com"
        assert result is mock_resp

    async def test_link_not_found_raises_404(self):
        mock_resp = MagicMock()
        mock_resp.headers = {}
        with patch("routes.links.cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            with patch("routes.links.LinkService") as MockSvc:
                MockSvc.return_value.get_by_short_code = AsyncMock(return_value=None)
                with pytest.raises(HTTPException) as exc:
                    await redirect_to_original("notexist", mock_resp)
        assert exc.value.status_code == 404
        assert "link not found" in exc.value.detail

    async def test_expired_link_raises_410(self):
        expired_link = _mock_link(
            expires_at=datetime.now() - timedelta(hours=1)
        )
        mock_resp = MagicMock()
        mock_resp.headers = {}
        with patch("routes.links.cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            with patch("routes.links.LinkService") as MockSvc:
                MockSvc.return_value.get_by_short_code = AsyncMock(
                    return_value=expired_link
                )
                with pytest.raises(HTTPException) as exc:
                    await redirect_to_original("oldcode", mock_resp)
        assert exc.value.status_code == 410
        assert "expired" in exc.value.detail

    async def test_valid_link_sets_location_and_records_click(self):
        valid_link = _mock_link(
            "val1", "https://target.com",
            expires_at=datetime.now() + timedelta(days=1)
        )
        mock_resp = MagicMock()
        mock_resp.headers = {}
        with patch("routes.links.cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.invalidate_link = AsyncMock()
            with patch("routes.links.LinkService") as MockSvc:
                svc_inst = MockSvc.return_value
                svc_inst.get_by_short_code = AsyncMock(return_value=valid_link)
                svc_inst.record_click = AsyncMock()
                result = await redirect_to_original("val1", mock_resp)
        assert mock_resp.headers["Location"] == "https://target.com"
        svc_inst.record_click.assert_awaited_once_with(valid_link)
        mock_cache.invalidate_link.assert_awaited_once_with("val1")

class TestUpdateLink:
    async def test_update_success_returns_link(self):
        link = _mock_link("upd1", "https://new.com")
        user = _mock_user()
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.update_link = AsyncMock(return_value=link)
            with patch("routes.links.cache") as mock_cache:
                mock_cache.invalidate_link = AsyncMock()
                link_upd = MagicMock()
                link_upd.original_url = "https://new.com"
                result = await update_link("upd1", link_upd, user)
        assert result is link
        mock_cache.invalidate_link.assert_awaited_once_with("upd1")

    async def test_update_error_raises_http_400(self):
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.update_link = AsyncMock(
                side_effect=ValueError("not authorized")
            )
            with patch("routes.links.cache"):
                with pytest.raises(HTTPException) as exc:
                    link_upd = MagicMock()
                    link_upd.original_url = "https://x.com"
                    await update_link("sc1", link_upd, _mock_user())
        assert exc.value.status_code == 400

class TestDeleteLink:
    async def test_delete_success_returns_ok(self):
        user = _mock_user()
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.delete_link = AsyncMock()
            with patch("routes.links.cache") as mock_cache:
                mock_cache.invalidate_link = AsyncMock()
                result = await delete_link("del1", user)
        assert result == {"status": "OK"}
        mock_cache.invalidate_link.assert_awaited_once_with("del1")

    async def test_delete_error_raises_http_400(self):
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.delete_link = AsyncMock(
                side_effect=ValueError("link not found")
            )
            with patch("routes.links.cache"):
                with pytest.raises(HTTPException) as exc:
                    await delete_link("ghost", _mock_user())
        assert exc.value.status_code == 400

class TestGetLinkStats:
    async def test_cache_hit_returns_cached_stats(self):
        cached = {
            "short_code": "sc1",
            "original_url": "https://x.com",
            "custom_alias": None,
            "created_at": "2024-01-01T00:00:00",
            "click_count": 5,
            "last_used_at": None,
            "expires_at": None,
        }
        with patch("routes.links.cache") as mock_cache:
            mock_cache.get_stats = AsyncMock(return_value=cached)
            result = await get_link_stats("sc1")
        assert result == cached

    async def test_link_not_found_raises_404(self):
        with patch("routes.links.cache") as mock_cache:
            mock_cache.get_stats = AsyncMock(return_value=None)
            with patch("routes.links.LinkService") as MockSvc:
                MockSvc.return_value.get_stats = AsyncMock(return_value=None)
                with pytest.raises(HTTPException) as exc:
                    await get_link_stats("ghost_stats")
        assert exc.value.status_code == 404

    async def test_link_found_returns_stats_and_caches(self):
        link = _mock_link("sc2", "https://stats.com")
        with patch("routes.links.cache") as mock_cache:
            mock_cache.get_stats = AsyncMock(return_value=None)
            mock_cache.set_stats = AsyncMock()
            with patch("routes.links.LinkService") as MockSvc:
                MockSvc.return_value.get_stats = AsyncMock(return_value=link)
                result = await get_link_stats("sc2")
        assert isinstance(result, LinkStats)
        assert result.short_code == "sc2"
        mock_cache.set_stats.assert_awaited_once()

class TestGetUserLinks:
    async def test_returns_user_links(self):
        user = _mock_user()
        links = [_mock_link("a"), _mock_link("b")]
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.get_user_links = AsyncMock(return_value=links)
            result = await get_user_links(user)
        assert result == links

    async def test_empty_list_when_no_links(self):
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.get_user_links = AsyncMock(return_value=[])
            result = await get_user_links(_mock_user())
        assert result == []

class TestGetProjectLinks:
    async def test_returns_project_links(self):
        user = _mock_user()
        links = [_mock_link("p1")]
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.get_project_links = AsyncMock(return_value=links)
            result = await get_project_links("myproj", user)
        assert result == links

class TestListExpiredLinks:
    async def test_returns_expired_links(self):
        user = _mock_user()
        links = [_mock_link("exp1", expires_at=datetime.now() - timedelta(days=1))]
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.get_expired_links = AsyncMock(return_value=links)
            result = await list_expired_links(user)
        assert result == links

class TestLinksViaTestClient:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        from main import app
        from deps import get_current_user, get_optional_user

        mock_user = _mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_optional_user] = lambda: None

        self.app = app
        self.client = TestClient(app, raise_server_exceptions=False)
        yield
        app.dependency_overrides.clear()

    def test_delete_link_not_found_returns_400(self):
        with patch("routes.links.LinkService") as MockSvc:
            MockSvc.return_value.delete_link = AsyncMock(
                side_effect=ValueError("link not found")
            )
            with patch("routes.links.cache") as mc:
                mc.invalidate_link = AsyncMock()
                resp = self.client.delete("/api/links/no_exist")
        assert resp.status_code == 400

    def test_stats_link_not_found_returns_404(self):
        with patch("routes.links.cache") as mc:
            mc.get_stats = AsyncMock(return_value=None)
            with patch("routes.links.LinkService") as MockSvc:
                MockSvc.return_value.get_stats = AsyncMock(return_value=None)
                resp = self.client.get("/api/links/no_stats_link/stats")
        assert resp.status_code == 404

    def test_redirect_not_found_returns_404(self):
        with patch("routes.links.cache") as mc:
            mc.get = AsyncMock(return_value=None)
            with patch("routes.links.LinkService") as MockSvc:
                MockSvc.return_value.get_by_short_code = AsyncMock(return_value=None)
                resp = self.client.get("/api/links/completely_missing_code")
        assert resp.status_code == 404

    def test_redirect_expired_returns_410(self):
        expired = _mock_link(
            "exp_http", "https://old.com",
            expires_at=datetime.now() - timedelta(hours=1)
        )
        with patch("routes.links.cache") as mc:
            mc.get = AsyncMock(return_value=None)
            with patch("routes.links.LinkService") as MockSvc:
                MockSvc.return_value.get_by_short_code = AsyncMock(
                    return_value=expired
                )
                resp = self.client.get("/api/links/exp_http")
        assert resp.status_code == 410
