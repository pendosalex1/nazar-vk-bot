import logging
import os
from collections.abc import Generator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import Base
from app.vk import check_vk_request, process_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nazar VK Bot",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Nazar VK Bot started")


@app.get("/")
async def root():
    return {"service": "Nazar VK Bot", "status": "running"}


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/vk/callback")
async def vk_callback(
    payload: dict,
    db: Session = Depends(get_db),
):
    event_type = payload.get("type")

    if event_type == "confirmation":
        expected_group = os.getenv("VK_GROUP_ID", "")
        code = os.getenv("VK_CONFIRMATION_CODE", "")

        if str(payload.get("group_id", "")) != expected_group:
            raise HTTPException(status_code=403, detail="Invalid group")

        if not code:
            raise HTTPException(
                status_code=503,
                detail="VK confirmation code is not configured",
            )

        return PlainTextResponse(code)

    if not check_vk_request(payload):
        raise HTTPException(status_code=403, detail="Invalid VK callback")

    if event_type == "message_new":
        await process_message(payload, db)

    return PlainTextResponse("ok")
