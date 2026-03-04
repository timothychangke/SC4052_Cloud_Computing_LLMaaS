"""
GET /track/click  —  logs the click event then 302-redirects to the advertiser.

This is the URL that gets embedded into the LLM's markdown links.
When the user clicks a sponsored product link in the React UI, they
hit this endpoint first.
"""

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.services.tracking import log_click

router = APIRouter()


@router.get("/track/click")
async def track_click(
    ad_id: str = Query(...),
    session_id: str = Query(...),
    redirect: str = Query(...),
):
    await log_click(session_id, ad_id, redirect)
    return RedirectResponse(url=redirect, status_code=302)
