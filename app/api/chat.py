"""OpenAI-compatible chat completions endpoint"""
import json
import time
import uuid
from typing import List, Optional, Dict, Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()


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
    # Additional parameters
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None


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
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
):
    """OpenAI-compatible chat completions endpoint with memory and RAG"""
    
    # Validate API key
    if authorization:
        api_key = authorization.replace("Bearer ", "")
        if api_key != settings.API_KEY and settings.API_KEY != "default-api-key":
            raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Get user ID from header or request
    user_id = x_user_id or request.user or "default"
    
    # Get services from app state
    services = req.app.state.services
    
    if not services.llm:
        raise HTTPException(status_code=503, detail="LLM service not available")
    
    try:
        # Convert messages to dict format
        messages = [msg.dict() for msg in request.messages]
        
        # Get relevant context from memory if available
        if services.memory and user_id != "default":
            try:
                context_memories = await services.memory.get_context(
                    db, user_id, messages, max_context_size=3
                )
                
                if context_memories:
                    # Add context to system message
                    context_text = "\n".join([
                        f"- {mem.content}" for mem in context_memories
                    ])
                    
                    system_message = {
                        "role": "system",
                        "content": f"Previous context from user's memory:\n{context_text}\n\nUse this context to provide personalized and consistent responses."
                    }
                    
                    # Insert at beginning after any existing system message
                    if messages and messages[0].get("role") == "system":
                        messages[0]["content"] += f"\n\n{system_message['content']}"
                    else:
                        messages.insert(0, system_message)
            except Exception as e:
                logger.warning(f"Failed to get memory context: {e}")
        
        # Store the conversation in memory for future reference
        if services.memory and user_id != "default" and request.messages:
            try:
                last_user_message = None
                for msg in reversed(request.messages):
                    if msg.role == "user":
                        last_user_message = msg.content
                        break
                
                if last_user_message:
                    await services.memory.add_memory(
                        db,
                        user_id,
                        last_user_message,
                        memory_type="conversation",
                        session_id=f"chat-{uuid.uuid4()}"
                    )
            except Exception as e:
                logger.warning(f"Failed to store memory: {e}")
        
        if request.stream:
            # Streaming response
            return StreamingResponse(
                stream_chat_completion(request, services, messages),
                media_type="text/event-stream"
            )
        else:
            # Regular response
            response = await generate_chat_completion(request, services, messages)
            
            # Store assistant response in memory
            if services.memory and user_id != "default" and response.choices:
                try:
                    assistant_response = response.choices[0].get("message", {}).get("content")
                    if assistant_response:
                        await services.memory.add_memory(
                            db,
                            user_id,
                            f"Assistant: {assistant_response}",
                            memory_type="conversation"
                        )
                except Exception as e:
                    logger.warning(f"Failed to store assistant response: {e}")
            
            return response
            
    except Exception as e:
        logger.error(f"Error in chat completion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_chat_completion(
    request: ChatCompletionRequest,
    services,
    messages: List[Dict]
) -> ChatCompletionResponse:
    """Generate a chat completion using OpenRouter"""
    
    # Call OpenRouter via LLM service
    response = await services.llm.chat_completion(
        messages=messages,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=False,
        top_p=request.top_p,
        frequency_penalty=request.frequency_penalty,
        presence_penalty=request.presence_penalty,
        stop=request.stop
    )
    
    # Format response to match OpenAI format
    completion_id = f"chatcmpl-{uuid.uuid4()}"
    
    return ChatCompletionResponse(
        id=completion_id,
        created=int(time.time()),
        model=request.model,
        choices=response.get("choices", []),
        usage=response.get("usage")
    )


async def stream_chat_completion(
    request: ChatCompletionRequest,
    services,
    messages: List[Dict]
) -> AsyncGenerator:
    """Stream a chat completion using OpenRouter"""
    
    completion_id = f"chatcmpl-{uuid.uuid4()}"
    
    try:
        # Get streaming response from OpenRouter
        stream = await services.llm.chat_completion(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            stop=request.stop
        )
        
        # Forward the stream with proper SSE formatting
        async for chunk in stream:
            # Rewrite chunk with our completion ID
            if "id" in chunk:
                chunk["id"] = completion_id
            
            yield f"data: {json.dumps(chunk)}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Error in streaming: {str(e)}")
        error_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {"content": f"\n\nError: {str(e)}"},
                "finish_reason": "error"
            }]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


@router.get("/models")
async def list_models(req: Request):
    """List available models"""
    
    services = req.app.state.services
    
    if services.llm:
        models = await services.llm.list_available_models()
        
        # Format for OpenAI compatibility
        return {
            "object": "list",
            "data": [
                {
                    "id": model.get("id"),
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "synapse",
                    "permission": [],
                    "root": model.get("id"),
                    "parent": None,
                } for model in models
            ]
        }
    else:
        # Return default models if service not available
        return {
            "object": "list",
            "data": [
                {
                    "id": "synapse",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "synapse",
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
                },
                {
                    "id": "synapse-code",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "synapse",
                }
            ]
        }


# Import logger
import logging
logger = logging.getLogger(__name__)