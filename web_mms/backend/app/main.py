import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "mms-web-backend"}


@app.exception_handler(Exception)
async def unhandled_error(_: Request, exc: Exception):
    logging.exception("Unhandled API error", exc_info=exc)
    return JSONResponse(status_code=500, content={"code": "internal_error", "message": "The request could not be completed."})
