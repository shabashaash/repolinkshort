from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from database import get_db
from models import User
from schemas import LinkCreate, LinkUpdate, LinkResponse, LinkStats, LinkShortenResponse
from services.link_service import LinkService
from deps import get_current_user, get_optional_user
from cache import cache

router = APIRouter()

def build_short_url(short_code: str) -> str:
    return f"/api/links/{short_code}"

@router.post("/shorten", response_model=LinkShortenResponse)
async def create_short_link(
    link_data,
    user = Depends(get_optional_user)
):
    try:
        service = LinkService()
        link = await service.create_link(
            original_url=link_data.original_url,
            user=user,
            custom_alias=link_data.custom_alias,
            project=link_data.project,
            expires_at=link_data.expires_at
        )
        return LinkShortenResponse(
            short_code=link.short_code,
            short_url=build_short_url(link.short_code),
            original_url=link.original_url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{short_code}")
async def redirect_to_original(short_code, response):
    cached = await cache.get(f"link:{short_code}")
    if cached:
        response.headers["Location"] = cached["original_url"]
        return response
    service = LinkService()
    link = await service.get_by_short_code(short_code)
    if not link:
        raise HTTPException(status_code=404, detail="link not found")
    if link.expires_at and link.expires_at < datetime.now():
        raise HTTPException(status_code=410, detail="link has expired")
    await service.record_click(link)
    await cache.invalidate_link(short_code)
    response.headers["Location"] = link.original_url
    return response

@router.put("/{short_code}", response_model=LinkResponse)
async def update_link(
    short_code,
    link_update,
    user = Depends(get_current_user)
):
    try:
        service = LinkService()
        link = await service.update_link(short_code, link_update.original_url, user)
        await cache.invalidate_link(short_code)
        return link
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{short_code}")
async def delete_link(short_code, user = Depends(get_current_user)):
    try:
        service = LinkService()
        await service.delete_link(short_code, user)
        await cache.invalidate_link(short_code)
        return {"status": "OK"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{short_code}/stats", response_model=LinkStats)
async def get_link_stats(short_code):
    cached = await cache.get_stats(short_code)
    if cached:
        return cached
    service = LinkService()
    link = await service.get_stats(short_code)
    if not link:
        raise HTTPException(status_code=404, detail="link not found")
    stats = LinkStats(
        short_code=link.short_code,
        original_url=link.original_url,
        custom_alias=link.custom_alias,
        created_at=link.created_at,
        click_count=link.click_count,
        last_used_at=link.last_used_at,
        expires_at=link.expires_at
    )
    await cache.set_stats(short_code, stats.model_dump())
    return stats

@router.get("/search", response_model=list[LinkResponse])
async def search_by_original(original_url = Query(...)):
    service = LinkService()
    return await service.search_by_url(original_url)

@router.get("/user/links", response_model=list[LinkResponse])
async def get_user_links(user = Depends(get_current_user)):
    service = LinkService()
    return await service.get_user_links(user)

@router.get("/project/{project}", response_model=list[LinkResponse])
async def get_project_links(project, user = Depends(get_current_user)):
    service = LinkService()
    return await service.get_project_links(project, user)

@router.get("/expired/list", response_model=list[LinkResponse])
async def list_expired_links(user = Depends(get_current_user)):
    service = LinkService()
    return await service.get_expired_links(user)