from models import User
from repositories.user_repository import UserRepository
from services.base import BaseService
from utils import hash_password, verify_password, create_access_token

class AuthService(BaseService):
    async def register(self, email, password):
        async with self.session() as session:
            repo = UserRepository(session)
            existing = await repo.get_by_email(email)
            if existing:
                raise ValueError("email already registered")
            user = await repo.create(email, hash_password(password))
            return user
    
    async def login(self, email, password):
        async with self.session() as session:
            repo = UserRepository(session)
            user = await repo.get_by_email(email)
            if not user or not verify_password(password, user.hashed_password):
                raise ValueError("incorrect email or password")
            return create_access_token(data={"sub": user.email})
    
    async def get_user_by_email(self, email):
        async with self.session() as session:
            repo = UserRepository(session)
            return await repo.get_by_email(email)