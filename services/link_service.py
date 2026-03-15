from typing import Optional
from datetime import datetime
from models import Link, User
from repositories.link_repository import LinkRepository
from services.base import BaseService
from utils import generate_short_code

class LinkService(BaseService):
    async def create_link(
        self,
        original_url,
        user = None,
        custom_alias = None,
        project = "default",
        expires_at = None
    ):
        from config import settings
        async with self.session() as session:
            repo = LinkRepository(session)
            if custom_alias:
                if await repo.alias_exists(custom_alias):
                    raise ValueError("Alias already in use")
                short_code = custom_alias
            else:
                while True:
                    short_code = generate_short_code()
                    if not await repo.code_exists(short_code):
                        break
            if not expires_at and settings.DEFAULT_LINK_EXPIRE_DAYS:
                expires_at = datetime.now() + timedelta(days=settings.DEFAULT_LINK_EXPIRE_DAYS)
            link = await repo.create(
                short_code=short_code,
                original_url=original_url,
                custom_alias=custom_alias,
                user_id=user.id if user else None,
                project=project,
                expires_at=expires_at
            )
            return link
    
    async def get_by_short_code(self, short_code):
        async with self.session() as session:
            repo = LinkRepository(session)
            return await repo.get_by_short_code(short_code)
    
    async def record_click(self, link):
        async with self.session() as session:
            repo = LinkRepository(session)
            await repo.increment_click(link)
    
    async def update_link(self, short_code, new_url, user):
        async with self.session() as session:
            repo = LinkRepository(session)
            link = await repo.get_by_short_code(short_code)
            if not link:
                raise ValueError("link not found")
            if link.user_id != user.id and not user.is_superuser:
                raise ValueError("not authorized")
            link.original_url = new_url
            return await repo.update(link)
    
    async def delete_link(self, short_code, user):
        async with self.session() as session:
            repo = LinkRepository(session)
            link = await repo.get_by_short_code(short_code)
            if not link:
                raise ValueError("link not found")
            if link.user_id != user.id and not user.is_superuser:
                raise ValueError("not authorized")
            await repo.delete(link)
    
    async def get_stats(self, short_code):
        return await self.get_by_short_code(short_code)
    
    async def search_by_url(self, original_url):
        async with self.session() as session:
            repo = LinkRepository(session)
            return await repo.get_by_original_url(original_url)
    
    async def get_user_links(self, user):
        async with self.session() as session:
            repo = LinkRepository(session)
            return await repo.get_by_user(user.id)
    
    async def get_project_links(self, project, user):
        async with self.session() as session:
            repo = LinkRepository(session)
            return await repo.get_by_project(project, user.id)
    
    async def get_expired_links(self, user):
        async with self.session() as session:
            repo = LinkRepository(session)
            return await repo.get_expired(user.id)