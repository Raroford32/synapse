"""Memory Service using Mem0 patterns with PostgreSQL"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory, MemoryRelation, UserProfile
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing user memory and context"""
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        
    async def add_memory(
        self,
        session: AsyncSession,
        user_id: str,
        content: str,
        memory_type: str = "general",
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Memory:
        """Add a new memory for a user"""
        
        try:
            # Generate embedding for the memory
            embedding = await self.embedding_service.generate_embedding(content)
            
            # Check for similar existing memories
            similar_memories = await self.find_similar_memories(
                session, user_id, embedding, threshold=0.9
            )
            
            # If very similar memory exists, update it instead
            if similar_memories and similar_memories[0]["similarity"] > 0.95:
                existing_memory = similar_memories[0]["memory"]
                existing_memory.content = content
                existing_memory.updated_at = datetime.utcnow()
                existing_memory.access_count += 1
                await session.commit()
                return existing_memory
            
            # Create new memory
            memory = Memory(
                user_id=user_id,
                session_id=session_id,
                content=content,
                memory_type=memory_type,
                embedding=embedding,
                metadata=metadata or {}
            )
            
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            
            # Create relations to similar memories if any
            if similar_memories:
                for similar in similar_memories[:3]:  # Link to top 3 similar
                    relation = MemoryRelation(
                        source_memory_id=memory.id,
                        target_memory_id=similar["memory"].id,
                        relation_type="similar",
                        strength=similar["similarity"]
                    )
                    session.add(relation)
                await session.commit()
            
            logger.info(f"Added memory for user {user_id}: {memory.id}")
            return memory
            
        except Exception as e:
            logger.error(f"Error adding memory: {str(e)}")
            await session.rollback()
            raise
    
    async def get_memories(
        self,
        session: AsyncSession,
        user_id: str,
        memory_type: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Memory]:
        """Get memories for a user"""
        
        query = select(Memory).where(Memory.user_id == user_id)
        
        if memory_type:
            query = query.where(Memory.memory_type == memory_type)
        
        if session_id:
            query = query.where(Memory.session_id == session_id)
        
        query = query.order_by(Memory.relevance_score.desc(), Memory.created_at.desc())
        query = query.limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    async def find_similar_memories(
        self,
        session: AsyncSession,
        user_id: str,
        embedding: List[float],
        threshold: float = 0.7,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar memories using vector similarity"""
        
        # Get all user memories with embeddings
        query = select(Memory).where(
            and_(
                Memory.user_id == user_id,
                Memory.embedding.isnot(None)
            )
        )
        
        result = await session.execute(query)
        memories = result.scalars().all()
        
        if not memories:
            return []
        
        # Calculate similarities
        embeddings = [m.embedding for m in memories]
        similarities = self.embedding_service.batch_cosine_similarity(
            embedding, embeddings
        )
        
        # Filter and sort results
        similar_memories = []
        for memory, similarity in zip(memories, similarities):
            if similarity >= threshold:
                similar_memories.append({
                    "memory": memory,
                    "similarity": similarity
                })
        
        # Sort by similarity
        similar_memories.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similar_memories[:limit]
    
    async def search_memories(
        self,
        session: AsyncSession,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> List[Memory]:
        """Search memories using semantic search"""
        
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)
        
        # Find similar memories
        similar_memories = await self.find_similar_memories(
            session, user_id, query_embedding, threshold=0.5, limit=limit
        )
        
        return [item["memory"] for item in similar_memories]
    
    async def get_context(
        self,
        session: AsyncSession,
        user_id: str,
        messages: List[Dict[str, str]],
        max_context_size: int = 5
    ) -> List[Memory]:
        """Get relevant context for a conversation"""
        
        if not messages:
            return []
        
        # Get embedding for the last user message
        last_user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        if not last_user_message:
            return []
        
        # Search for relevant memories
        relevant_memories = await self.search_memories(
            session, user_id, last_user_message, limit=max_context_size
        )
        
        # Update access count for retrieved memories
        for memory in relevant_memories:
            memory.access_count += 1
            memory.relevance_score = min(
                memory.relevance_score * 1.1, 10.0
            )  # Increase relevance
        
        await session.commit()
        
        return relevant_memories
    
    async def update_user_profile(
        self,
        session: AsyncSession,
        user_id: str,
        updates: Dict[str, Any]
    ) -> UserProfile:
        """Update or create user profile"""
        
        # Get existing profile
        query = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await session.execute(query)
        profile = result.scalar_one_or_none()
        
        if profile:
            # Update existing profile
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = datetime.utcnow()
            profile.total_interactions += 1
        else:
            # Create new profile
            profile = UserProfile(
                user_id=user_id,
                **updates,
                total_interactions=1
            )
            session.add(profile)
        
        await session.commit()
        await session.refresh(profile)
        
        return profile
    
    async def get_user_profile(
        self,
        session: AsyncSession,
        user_id: str
    ) -> Optional[UserProfile]:
        """Get user profile"""
        
        query = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def cleanup_old_memories(
        self,
        session: AsyncSession,
        user_id: str,
        days: int = 30,
        keep_important: bool = True
    ):
        """Clean up old memories while preserving important ones"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = delete(Memory).where(
            and_(
                Memory.user_id == user_id,
                Memory.created_at < cutoff_date
            )
        )
        
        if keep_important:
            # Keep memories with high relevance or access count
            query = query.where(
                and_(
                    Memory.relevance_score < 5.0,
                    Memory.access_count < 10
                )
            )
        
        await session.execute(query)
        await session.commit()
        
        logger.info(f"Cleaned up old memories for user {user_id}")
    
    async def consolidate_memories(
        self,
        session: AsyncSession,
        user_id: str
    ):
        """Consolidate similar memories to reduce redundancy"""
        
        # Get all user memories
        query = select(Memory).where(Memory.user_id == user_id)
        result = await session.execute(query)
        memories = result.scalars().all()
        
        if len(memories) < 2:
            return
        
        # Group highly similar memories
        consolidated = []
        processed = set()
        
        for i, memory in enumerate(memories):
            if memory.id in processed:
                continue
            
            # Find memories similar to this one
            if memory.embedding:
                similar = await self.find_similar_memories(
                    session, user_id, memory.embedding, threshold=0.85
                )
                
                if len(similar) > 1:
                    # Consolidate into a single memory
                    combined_content = memory.content
                    for sim in similar[1:]:  # Skip first (itself)
                        if sim["memory"].id not in processed:
                            combined_content += f"\n{sim['memory'].content}"
                            processed.add(sim["memory"].id)
                            # Mark for deletion
                            await session.delete(sim["memory"])
                    
                    # Update the main memory
                    memory.content = combined_content
                    memory.updated_at = datetime.utcnow()
                    consolidated.append(memory)
        
        await session.commit()
        
        logger.info(f"Consolidated {len(processed)} memories for user {user_id}")