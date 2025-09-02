"""Document models for R2R integration"""
from sqlalchemy import Column, String, Text, JSON, Float, Integer, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TSVECTOR
from pgvector.sqlalchemy import Vector
from app.models.base import BaseModel


class Document(BaseModel):
    """Document storage model"""
    __tablename__ = "documents"
    __table_args__ = {"schema": "r2r"}
    
    user_id = Column(String, nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer)
    content = Column(Text)
    metadata = Column(JSON, default={})
    is_processed = Column(Boolean, default=False)
    processing_error = Column(Text)
    search_vector = Column(TSVECTOR)
    
    # Indexes
    __table_args__ = (
        Index("idx_document_user", "user_id"),
        Index("idx_document_search", "search_vector", postgresql_using="gin"),
        {"schema": "r2r"}
    )


class DocumentChunk(BaseModel):
    """Document chunks for RAG"""
    __tablename__ = "document_chunks"
    __table_args__ = {"schema": "r2r"}
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("r2r.documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    metadata = Column(JSON, default={})
    token_count = Column(Integer)
    start_char = Column(Integer)
    end_char = Column(Integer)
    
    # Indexes
    __table_args__ = (
        Index("idx_chunk_document", "document_id"),
        Index("idx_chunk_embedding", "embedding", postgresql_using="ivfflat"),
        {"schema": "r2r"}
    )


class Collection(BaseModel):
    """Document collections for organization"""
    __tablename__ = "collections"
    __table_args__ = {"schema": "r2r"}
    
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    metadata = Column(JSON, default={})
    is_public = Column(Boolean, default=False)
    document_count = Column(Integer, default=0)


class DocumentCollection(BaseModel):
    """Many-to-many relationship between documents and collections"""
    __tablename__ = "document_collections"
    __table_args__ = {"schema": "r2r"}
    
    document_id = Column(UUID(as_uuid=True), ForeignKey("r2r.documents.id"), nullable=False)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("r2r.collections.id"), nullable=False)
    added_by = Column(String)
    metadata = Column(JSON, default={})