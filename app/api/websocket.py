"""WebSocket endpoints for real-time streaming"""
import json
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manager for WebSocket connections"""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, user_id: str, websocket: WebSocket):
        """Accept and store connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")
    
    def disconnect(self, user_id: str):
        """Remove connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_message(self, user_id: str, message: dict):
        """Send message to specific user"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections"""
        for websocket in self.active_connections.values():
            await websocket.send_json(message)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/chat/{user_id}")
async def websocket_chat(
    websocket: WebSocket,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for streaming chat"""
    
    await manager.connect(user_id, websocket)
    
    # Get services from app state
    services = websocket.app.state.services
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "user_id": user_id
        })
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(
            send_heartbeat(websocket, user_id)
        )
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            message_type = data.get("type", "chat")
            
            if message_type == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})
                
            elif message_type == "chat":
                # Process chat message
                await process_chat_message(
                    websocket, user_id, data, services, db
                )
                
            elif message_type == "search":
                # Process search request
                await process_search_request(
                    websocket, user_id, data, services, db
                )
                
            elif message_type == "memory":
                # Process memory request
                await process_memory_request(
                    websocket, user_id, data, services, db
                )
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        heartbeat_task.cancel()
        logger.info(f"WebSocket disconnected for user {user_id}")
        
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        manager.disconnect(user_id)
        heartbeat_task.cancel()


async def send_heartbeat(websocket: WebSocket, user_id: str):
    """Send periodic heartbeat to keep connection alive"""
    
    try:
        while True:
            await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
            await websocket.send_json({"type": "heartbeat"})
    except Exception:
        # Connection closed
        pass


async def process_chat_message(
    websocket: WebSocket,
    user_id: str,
    data: dict,
    services,
    db: AsyncSession
):
    """Process chat message and stream response"""
    
    if not services.llm:
        await websocket.send_json({
            "type": "error",
            "message": "LLM service not available"
        })
        return
    
    try:
        messages = data.get("messages", [])
        model = data.get("model", "synapse")
        temperature = data.get("temperature", 0.7)
        max_tokens = data.get("max_tokens")
        
        # Get memory context if available
        if services.memory and user_id != "default":
            try:
                context_memories = await services.memory.get_context(
                    db, user_id, messages, max_context_size=3
                )
                
                if context_memories:
                    context_text = "\n".join([
                        f"- {mem.content}" for mem in context_memories
                    ])
                    
                    system_message = {
                        "role": "system",
                        "content": f"Previous context:\n{context_text}"
                    }
                    
                    if messages and messages[0].get("role") == "system":
                        messages[0]["content"] += f"\n\n{system_message['content']}"
                    else:
                        messages.insert(0, system_message)
                        
            except Exception as e:
                logger.warning(f"Failed to get memory context: {e}")
        
        # Send start message
        await websocket.send_json({
            "type": "start",
            "model": model
        })
        
        # Stream response from LLM
        full_response = ""
        
        stream = await services.llm.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        
        async for chunk in stream:
            # Extract content from chunk
            if "choices" in chunk and chunk["choices"]:
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                
                if content:
                    full_response += content
                    
                    # Send chunk to client
                    await websocket.send_json({
                        "type": "chunk",
                        "content": content
                    })
                
                # Check for finish reason
                finish_reason = chunk["choices"][0].get("finish_reason")
                if finish_reason:
                    await websocket.send_json({
                        "type": "end",
                        "finish_reason": finish_reason
                    })
                    break
        
        # Store conversation in memory
        if services.memory and user_id != "default" and full_response:
            try:
                # Store user message
                last_user_message = None
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        last_user_message = msg.get("content")
                        break
                
                if last_user_message:
                    await services.memory.add_memory(
                        db,
                        user_id,
                        last_user_message,
                        memory_type="conversation"
                    )
                
                # Store assistant response
                await services.memory.add_memory(
                    db,
                    user_id,
                    f"Assistant: {full_response}",
                    memory_type="conversation"
                )
                
            except Exception as e:
                logger.warning(f"Failed to store memory: {e}")
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


async def process_search_request(
    websocket: WebSocket,
    user_id: str,
    data: dict,
    services,
    db: AsyncSession
):
    """Process search request"""
    
    query = data.get("query", "")
    search_type = data.get("search_type", "all")  # all, documents, memories
    
    try:
        results = {
            "type": "search_results",
            "query": query,
            "documents": [],
            "memories": []
        }
        
        # Search documents
        if search_type in ["all", "documents"] and services.rag:
            doc_results = await services.rag.search_documents(
                db, user_id, query, limit=5
            )
            
            results["documents"] = [
                {
                    "document_id": str(r["document"].id),
                    "filename": r["document"].filename,
                    "content": r["content"][:200] + "...",
                    "similarity": r["similarity"]
                }
                for r in doc_results
            ]
        
        # Search memories
        if search_type in ["all", "memories"] and services.memory:
            mem_results = await services.memory.search_memories(
                db, user_id, query, limit=5
            )
            
            results["memories"] = [
                {
                    "id": str(mem.id),
                    "content": mem.content,
                    "type": mem.memory_type,
                    "created_at": mem.created_at.isoformat()
                }
                for mem in mem_results
            ]
        
        await websocket.send_json(results)
        
    except Exception as e:
        logger.error(f"Error processing search: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


async def process_memory_request(
    websocket: WebSocket,
    user_id: str,
    data: dict,
    services,
    db: AsyncSession
):
    """Process memory-related requests"""
    
    action = data.get("action", "get")
    
    try:
        if action == "get":
            # Get memories
            memories = await services.memory.get_memories(
                db, user_id, limit=10
            )
            
            await websocket.send_json({
                "type": "memories",
                "memories": [
                    {
                        "id": str(mem.id),
                        "content": mem.content,
                        "type": mem.memory_type,
                        "created_at": mem.created_at.isoformat()
                    }
                    for mem in memories
                ]
            })
            
        elif action == "add":
            # Add memory
            content = data.get("content", "")
            memory_type = data.get("memory_type", "general")
            
            mem = await services.memory.add_memory(
                db, user_id, content, memory_type
            )
            
            await websocket.send_json({
                "type": "memory_added",
                "memory": {
                    "id": str(mem.id),
                    "content": mem.content,
                    "type": mem.memory_type
                }
            })
            
    except Exception as e:
        logger.error(f"Error processing memory request: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })