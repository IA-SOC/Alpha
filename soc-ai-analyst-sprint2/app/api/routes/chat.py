
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from agent.llm import ProviderUnavailable
from app.schemas.chat import AnalystMessage
from app.services.chat_service import ChatService, InvalidModelAnswer

router = APIRouter(prefix="/api/v1/cases", tags=["conversation"])


def get_chat(request: Request) -> ChatService:
    return request.app.state.chat_service


Service = Annotated[ChatService, Depends(get_chat)]


@router.get("/{case_id}/messages")
def messages(case_id: UUID, service: Service):
    if service.store.get_by_id(case_id) is None:
        raise HTTPException(404, "Case not found")
    return {"case_id": str(case_id), "messages": service.store.messages(case_id)}


@router.get("/{case_id}/chat-evidence")
def evidence(case_id: UUID, service: Service):
    try:
        return {"case_id": str(case_id), "evidence": service.evidence(case_id)}
    except KeyError as exc:
        raise HTTPException(404, "Case not found") from exc
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/{case_id}/messages")
async def send_message(
    case_id: UUID,
    message: AnalystMessage,
    service: Service,
    analyst_header: Annotated[str, Header(alias="X-Analyst-Id")],
):
    if analyst_header != message.analyst_id:
        raise HTTPException(403, "X-Analyst-Id does not match analyst_id")
    try:
        return await service.send(case_id, message)
    except KeyError as exc:
        raise HTTPException(404, "Case not found") from exc
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ProviderUnavailable as exc:
        raise HTTPException(503, "Gemini is not configured") from exc
    except TimeoutError as exc:
        raise HTTPException(504, "Gemini conversation timed out") from exc
    except InvalidModelAnswer as exc:
        raise HTTPException(502, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Gemini conversation failed") from exc
