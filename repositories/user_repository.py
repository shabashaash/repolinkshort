from sqlalchemy import select
from typing import Optional
from models import User
from repositories.base import BaseRepository

class UserRepository(BaseRepository):
    async def create(self, email, hashed_password):
        user = User(email=email, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def get_by_email(self, email):
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_id(self, user_id):
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()