from fastapi import APIRouter

from app.core.responses import DataResponse, build_data_payload

router = APIRouter()


@router.get("/health", response_model=DataResponse[dict[str, str]])
async def health_check() -> dict[str, dict[str, str]]:
    return build_data_payload({"status": "ok"})
