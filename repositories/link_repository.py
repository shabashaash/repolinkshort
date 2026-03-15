from sqlalchemy import select, or_, and_
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
from models import Link
from repositories.base import BaseRepository

class LinkRepository(BaseRepository):
    async def create(self, short_code, original_url, **kwargs):
        link = Link(short_code=short_code, original_url=original_url, **kwargs)
        self.db.add(link)
        await self.db.commit()
        await self.db.refresh(link)
        return link
    
    async def get_by_short_code(self, short_code):
        result = await self.db.execute(
            select(Link).where(Link.short_code == short_code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_custom_alias(self, alias):
        result = await self.db.execute(
            select(Link).where(Link.custom_alias == alias)
        )
        return result.scalar_one_or_none()
    
    async def get_by_original_url(self, original_url):
        result = await self.db.execute(
            select(Link).where(Link.original_url == original_url)
        )
        return list(result.scalars().all())
    
    async def get_by_user(self, user_id):
        result = await self.db.execute(
            select(Link).where(Link.user_id == user_id).order_by(Link.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_by_project(self, project, user_id):
        result = await self.db.execute(
            select(Link).where(Link.project == project, Link.user_id == user_id)
        )
        return list(result.scalars().all())
    
    async def update(self, link):
        await self.db.commit()
        await self.db.refresh(link)
        return link
    
    async def delete(self, link):
        await self.db.delete(link)
        await self.db.commit()
    
    async def increment_click(self, link):
        link.click_count += 1
        link.last_used_at = datetime.now()
        await self.db.commit()
    
    async def get_expired(self, user_id = None):
        query = select(Link).where(Link.expires_at < datetime.now())
        if user_id:
            query = query.where(Link.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_unused(self, cutoff, user_id = None):
        query = select(Link).where(
            or_(
                Link.last_used_at < cutoff,
                Link.last_used_at.is_(None)
            ),
            Link.created_at < cutoff
        )
        if user_id:
            query = query.where(Link.user_id == user_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def code_exists(self, short_code):
        result = await self.db.execute(
            select(Link).where(Link.short_code == short_code)
        )
        return result.scalar_one_or_none() is not None
    
    async def alias_exists(self, alias):
        result = await self.db.execute(
            select(Link).where(
                or_(Link.custom_alias == alias, Link.short_code == alias)
            )
        )
        return result.scalar_one_or_none() is not None