"""Memory models for Mem0 integration"""
from sqlalchemy import Column, String, Text, JSON, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from pgvector.sqlalchemy import Vector
from app.models.base import BaseModel
import uuid


class Memory(BaseModel):
    """Memory storage model"""
    __tablename__ = "memories"
    __table_args__ = {"schema": "mem0"}
    
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, index=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String, default="general")  # general, procedural, preference, fact
    embedding = Column(Vector(1536))
    metadata = Column(JSON, default={})
    relevance_score = Column(Float, default=1.0)
    access_count = Column(Float, default=0)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_memory_user_type", "user_id", "memory_type"),
        Index("idx_memory_embedding", "embedding", postgresql_using="ivfflat"),
        {"schema": "mem0"}
    )


class MemoryRelation(BaseModel):
    """Relationships between memories"""
    __tablename__ = "memory_relations"
    __table_args__ = {"schema": "mem0"}
    
    source_memory_id = Column(UUID(as_uuid=True), ForeignKey("mem0.memories.id"))
    target_memory_id = Column(UUID(as_uuid=True), ForeignKey("mem0.memories.id"))
    relation_type = Column(String, nullable=False)  # similar, contradicts, extends, replaces
    strength = Column(Float, default=1.0)
    metadata = Column(JSON, default={})


class UserProfile(BaseModel):
    """User profile for personalization"""
    __tablename__ = "user_profiles"
    __table_args__ = {"schema": "mem0"}
    
    user_id = Column(String, unique=True, nullable=False, index=True)
    preferences = Column(JSON, default={})
    expertise_areas = Column(ARRAY(String), default=[])
    interaction_style = Column(String, default="balanced")  # technical, simple, detailed, concise
    context_retention = Column(String, default="session")  # session, persistent, adaptive
    metadata = Column(JSON, default={})
    total_interactions = Column(Float, default=0)
    last_interaction = Column(String)