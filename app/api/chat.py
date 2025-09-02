"""OpenAI-compatible chat completions endpoint"""
import time
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Header, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import require_api_key
from app.core.services import ServiceManager

router = APIRouter(dependencies=[Depends(require_api_key)])


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "synapse"
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    user: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    req: Request,
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """OpenAI-compatible chat completions endpoint"""
    
    # Get user ID from header or request
    user_id = x_user_id or request.user or "default"
    
    # Get services from app state
    services = req.app.state.services
    
    try:
        if request.stream:
            # Streaming response via LLM service
            return StreamingResponse(
                services.llm.stream_chat_completion(
                    model=request.model,
                    messages=[m.model_dump() for m in request.messages],
                    temperature=request.temperature or 0.7,
                    max_tokens=request.max_tokens,
                    user_id=user_id,
                ),
                media_type="text/event-stream",
            )
        else:
            # Regular response via LLM service
            result = await services.llm.create_chat_completion(
                model=request.model,
                messages=[m.model_dump() for m in request.messages],
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens,
                user_id=user_id,
            )
            return result
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_chat_completion(
    request: ChatCompletionRequest,
    services,
    user_id: str
) -> ChatCompletionResponse:
    """Deprecated: kept for compatibility; not used after service wiring."""
    result = await services.llm.create_chat_completion(
        model=request.model,
        messages=[m.model_dump() for m in request.messages],
        temperature=request.temperature or 0.7,
        max_tokens=request.max_tokens,
        user_id=user_id,
    )
    return ChatCompletionResponse(**result)


async def stream_chat_completion(request, services, user_id):
    """Deprecated: Use services.llm.stream_chat_completion directly."""
    async for chunk in services.llm.stream_chat_completion(
        model=request.model,
        messages=[m.model_dump() for m in request.messages],
        temperature=request.temperature or 0.7,
        max_tokens=request.max_tokens,
        user_id=user_id,
    ):
        yield chunk


@router.get("/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": "synapse",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "synapse",
                "permission": [],
                "root": "synapse",
                "parent": None,
            },
            {
                "id": "synapse-fast",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "synapse",
            },
            {
                "id": "synapse-smart",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "synapse",
            }
        ]
    }


@router.websocket("/ws/chat/{user_id}")
async def chat_ws(websocket: WebSocket, user_id: str):
    await websocket.accept()
    services: ServiceManager = websocket.app.state.services
    try:
        while True:
            data = await websocket.receive_json()
            messages = data.get("messages") or [{"role": "user", "content": data.get("message", "")}]
            async for chunk in services.llm.stream_chat_completion(
                model=data.get("model", "synapse"), messages=messages, user_id=user_id
            ):
                await websocket.send_text(chunk)
    except WebSocketDisconnect:
        await websocket.close()