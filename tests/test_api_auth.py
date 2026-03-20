import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from routes.auth import register, login
from models import User

def _mock_user(uid=1, email="user@example.com"):
    u = MagicMock(spec=User)
    u.id = uid
    u.email = email
    u.is_active = True
    u.is_superuser = False
    return u

def _mock_req(email="test@example.com", password="pass"):
    req = MagicMock()
    req.email = email
    req.password = password
    return req

class TestRegisterHandler:
    async def test_success_returns_user(self):
        user = _mock_user(email="new@example.com")
        with patch("routes.auth.AuthService") as MockSvc:
            MockSvc.return_value.register = AsyncMock(return_value=user)
            result = await register(user=_mock_req("new@example.com"), db=None)
        assert result is user
        MockSvc.return_value.register.assert_awaited_once_with(
            "new@example.com", "pass"
        )

    async def test_duplicate_email_raises_http_400(self):
        with patch("routes.auth.AuthService") as MockSvc:
            MockSvc.return_value.register = AsyncMock(
                side_effect=ValueError("email already registered")
            )
            with pytest.raises(HTTPException) as exc:
                await register(user=_mock_req(), db=None)
        assert exc.value.status_code == 400
        assert "email already registered" in exc.value.detail

    async def test_any_value_error_becomes_http_400(self):
        with patch("routes.auth.AuthService") as MockSvc:
            MockSvc.return_value.register = AsyncMock(
                side_effect=ValueError("custom error")
            )
            with pytest.raises(HTTPException) as exc:
                await register(user=_mock_req(), db=None)
        assert exc.value.status_code == 400

class TestLoginHandler:
    async def test_success_returns_token_dict(self):
        with patch("routes.auth.AuthService") as MockSvc:
            MockSvc.return_value.login = AsyncMock(return_value="jwt.token.here")
            form = MagicMock()
            form.username = "user@example.com"
            form.password = "secret"
            result = await login(form_data=form)
        assert result["access_token"] == "jwt.token.here"
        assert result["token_type"] == "bearer"

    async def test_wrong_credentials_raises_http_401(self):
        with patch("routes.auth.AuthService") as MockSvc:
            MockSvc.return_value.login = AsyncMock(
                side_effect=ValueError("incorrect email or password")
            )
            form = MagicMock()
            form.username = "x@x.com"
            form.password = "wrong"
            with pytest.raises(HTTPException) as exc:
                await login(form_data=form)
        assert exc.value.status_code == 401

    async def test_any_value_error_becomes_http_401(self):
        with patch("routes.auth.AuthService") as MockSvc:
            MockSvc.return_value.login = AsyncMock(
                side_effect=ValueError("some auth error")
            )
            form = MagicMock()
            form.username = "a@a.com"
            form.password = "p"
            with pytest.raises(HTTPException) as exc:
                await login(form_data=form)
        assert exc.value.status_code == 401

class TestAuthRoutesViaTestClient:
    @pytest.fixture(autouse=True)
    def app_client(self):
        from main import app
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_register_without_body_returns_422_or_404(self):
        resp = self.client.post("/api/auth/register")
        assert resp.status_code in (422, 400, 404, 405)

    def test_login_without_form_returns_422_or_error(self):
        resp = self.client.post("/api/auth/login")
        assert resp.status_code in (422, 400, 401, 404)
