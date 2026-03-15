from repositories.base import BaseRepository
from database import async_session_maker

class BaseService:
    def __init__(self):
        self.session = async_session_maker
    
    async def get_repo(self):
        async with self.session() as session:
            return BaseRepository(session)