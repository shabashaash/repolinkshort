from celery_app import celery_app
from database import async_session_maker
from repositories.link_repository import LinkRepository

@celery_app.task
def cleanup_expired_links():
    import asyncio
    async def _cleanup():
        async with async_session_maker() as session:
            repo = LinkRepository(session)
            expired = await repo.get_expired()
            for link in expired:
                await repo.delete(link)
            return {"deleted": len(expired)}
    return asyncio.run(_cleanup())

@celery_app.task
def cleanup_unused_links():
    import asyncio
    from datetime import datetime, timedelta
    from config import settings
    async def _cleanup():
        cutoff = datetime.now() - timedelta(days=settings.UNUSED_LINK_DELETE_DAYS)
        async with async_session_maker() as session:
            repo = LinkRepository(session)
            unused = await repo.get_unused(cutoff)
            for link in unused:
                await repo.delete(link)
            return {"deleted": len(unused)}
    return asyncio.run(_cleanup())