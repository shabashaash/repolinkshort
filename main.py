from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="URL Shortener Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes import auth, links
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(links.router, prefix="/api/links", tags=["links"])