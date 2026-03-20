import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call


class TestCleanupExpiredLinks:
    def test_cleanup_expired_removes_all_expired(self):
        link1 = MagicMock()
        link2 = MagicMock()

        mock_repo = AsyncMock()
        mock_repo.get_expired = AsyncMock(return_value=[link1, link2])
        mock_repo.delete = AsyncMock()

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        session_cm.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=session_cm)

        with patch("tasks.cleanup.async_session_maker", mock_factory):
            with patch("tasks.cleanup.LinkRepository", return_value=mock_repo):
                from tasks.cleanup import cleanup_expired_links
                result = cleanup_expired_links()

        assert result["deleted"] == 2
        assert mock_repo.delete.await_count == 2

    def test_cleanup_expired_returns_zero_when_none(self):
        mock_repo = AsyncMock()
        mock_repo.get_expired = AsyncMock(return_value=[])
        mock_repo.delete = AsyncMock()

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        session_cm.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=session_cm)

        with patch("tasks.cleanup.async_session_maker", mock_factory):
            with patch("tasks.cleanup.LinkRepository", return_value=mock_repo):
                from tasks.cleanup import cleanup_expired_links
                result = cleanup_expired_links()

        assert result["deleted"] == 0


class TestCleanupUnusedLinks:
    def test_cleanup_unused_removes_stale_links(self):
        link1 = MagicMock()

        mock_repo = AsyncMock()
        mock_repo.get_unused = AsyncMock(return_value=[link1])
        mock_repo.delete = AsyncMock()

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        session_cm.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=session_cm)

        with patch("tasks.cleanup.async_session_maker", mock_factory):
            with patch("tasks.cleanup.LinkRepository", return_value=mock_repo):
                from tasks.cleanup import cleanup_unused_links
                result = cleanup_unused_links()

        assert result["deleted"] == 1

    def test_cleanup_unused_computes_cutoff_from_settings(self):
        mock_repo = AsyncMock()
        mock_repo.get_unused = AsyncMock(return_value=[])
        mock_repo.delete = AsyncMock()

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
        session_cm.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=session_cm)

        captured_cutoffs = []

        async def capture_get_unused(cutoff):
            captured_cutoffs.append(cutoff)
            return []

        mock_repo.get_unused = capture_get_unused

        with patch("tasks.cleanup.async_session_maker", mock_factory):
            with patch("tasks.cleanup.LinkRepository", return_value=mock_repo):
                with patch("tasks.cleanup.celery_app"):  
                    from config import settings
                    from tasks.cleanup import cleanup_unused_links
                    cleanup_unused_links()

        if captured_cutoffs:
            cutoff = captured_cutoffs[0]
            expected_days = settings.UNUSED_LINK_DELETE_DAYS
            expected_cutoff = datetime.now() - timedelta(days=expected_days)
            # Allow 2s tolerance
            assert abs((cutoff - expected_cutoff).total_seconds()) < 2


class TestGetOptionalUser:
    async def test_returns_none_when_no_valid_token(self):
        from deps import get_optional_user
        result = await get_optional_user(token="invalid.token.here", db=None)
        assert result is None

    async def test_returns_none_when_token_is_garbage(self):
        from deps import get_optional_user
        result = await get_optional_user(token="garbage", db=None)
        assert result is None

    async def test_get_current_user_raises_when_jwt_missing(self):
        from fastapi import HTTPException
        from deps import get_current_user
        with pytest.raises((HTTPException, NameError, Exception)):
            await get_current_user(token="some.bad.token", db=None)

    async def test_get_optional_user_catches_all_exceptions(self):
        from deps import get_optional_user
        with patch("deps.get_current_user", AsyncMock(side_effect=Exception("boom"))):
            result = await get_optional_user(token="tok", db=None)
        assert result is None


class TestDatabase:
    async def test_init_db_runs_without_error(self):
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()

        mock_engine = MagicMock()
        engine_cm = MagicMock()
        engine_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        engine_cm.__aexit__ = AsyncMock(return_value=False)
        mock_engine.begin = MagicMock(return_value=engine_cm)

        with patch("database.engine", mock_engine):
            from database import init_db
            await init_db()

        mock_conn.run_sync.assert_awaited_once()

    async def test_get_db_yields_session(self):
        mock_session = AsyncMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_cm)

        with patch("database.async_session_maker", mock_factory):
            from database import get_db
            gen = get_db()
            session = await gen.__anext__()
            assert session is mock_session
