"""Initial schema creation

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create schemas
    op.execute('CREATE SCHEMA IF NOT EXISTS r2r')
    op.execute('CREATE SCHEMA IF NOT EXISTS mem0')
    op.execute('CREATE SCHEMA IF NOT EXISTS shared')
    
    # Create shared entities table
    op.create_table(
        'entities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('embedding', Vector(1536)),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('source_system', sa.Text()),
        schema='shared'
    )
    
    # Create shared relationships table
    op.create_table(
        'relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('from_entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shared.entities.id', ondelete='CASCADE')),
        sa.Column('to_entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shared.entities.id', ondelete='CASCADE')),
        sa.Column('relationship_type', sa.Text(), nullable=False),
        sa.Column('properties', postgresql.JSONB(), default={}),
        sa.Column('weight', sa.Float(), default=1.0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('source_system', sa.Text()),
        schema='shared'
    )
    
    # Create mem0 tables
    op.create_table(
        'memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('session_id', sa.String(), index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('memory_type', sa.String(), default='general'),
        sa.Column('embedding', Vector(1536)),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('relevance_score', sa.Float(), default=1.0),
        sa.Column('access_count', sa.Float(), default=0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        schema='mem0'
    )
    
    op.create_table(
        'memory_relations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('source_memory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('mem0.memories.id')),
        sa.Column('target_memory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('mem0.memories.id')),
        sa.Column('relation_type', sa.String(), nullable=False),
        sa.Column('strength', sa.Float(), default=1.0),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        schema='mem0'
    )
    
    op.create_table(
        'user_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.String(), unique=True, nullable=False, index=True),
        sa.Column('preferences', postgresql.JSONB(), default={}),
        sa.Column('expertise_areas', postgresql.ARRAY(sa.String()), default=[]),
        sa.Column('interaction_style', sa.String(), default='balanced'),
        sa.Column('context_retention', sa.String(), default='session'),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('total_interactions', sa.Float(), default=0),
        sa.Column('last_interaction', sa.String()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        schema='mem0'
    )
    
    # Create r2r tables
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer()),
        sa.Column('content', sa.Text()),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('is_processed', sa.Boolean(), default=False),
        sa.Column('processing_error', sa.Text()),
        sa.Column('search_vector', postgresql.TSVECTOR()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        schema='r2r'
    )
    
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('r2r.documents.id'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536)),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('token_count', sa.Integer()),
        sa.Column('start_char', sa.Integer()),
        sa.Column('end_char', sa.Integer()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        schema='r2r'
    )
    
    op.create_table(
        'collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('document_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        schema='r2r'
    )
    
    op.create_table(
        'document_collections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('r2r.documents.id'), nullable=False),
        sa.Column('collection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('r2r.collections.id'), nullable=False),
        sa.Column('added_by', sa.String()),
        sa.Column('metadata', postgresql.JSONB(), default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        schema='r2r'
    )
    
    # Create indexes
    op.create_index('idx_entities_embedding', 'entities', ['embedding'], schema='shared', postgresql_using='ivfflat')
    op.create_index('idx_entities_name', 'entities', ['name'], schema='shared')
    op.create_index('idx_entities_type', 'entities', ['type'], schema='shared')
    op.create_index('idx_relationships_from_to', 'relationships', ['from_entity_id', 'to_entity_id'], schema='shared')
    
    op.create_index('idx_memory_user_type', 'memories', ['user_id', 'memory_type'], schema='mem0')
    op.create_index('idx_memory_embedding', 'memories', ['embedding'], schema='mem0', postgresql_using='ivfflat')
    
    op.create_index('idx_document_user', 'documents', ['user_id'], schema='r2r')
    op.create_index('idx_document_search', 'documents', ['search_vector'], schema='r2r', postgresql_using='gin')
    op.create_index('idx_chunk_document', 'document_chunks', ['document_id'], schema='r2r')
    op.create_index('idx_chunk_embedding', 'document_chunks', ['embedding'], schema='r2r', postgresql_using='ivfflat')


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('document_collections', schema='r2r')
    op.drop_table('collections', schema='r2r')
    op.drop_table('document_chunks', schema='r2r')
    op.drop_table('documents', schema='r2r')
    
    op.drop_table('user_profiles', schema='mem0')
    op.drop_table('memory_relations', schema='mem0')
    op.drop_table('memories', schema='mem0')
    
    op.drop_table('relationships', schema='shared')
    op.drop_table('entities', schema='shared')
    
    # Drop schemas
    op.execute('DROP SCHEMA IF EXISTS r2r CASCADE')
    op.execute('DROP SCHEMA IF EXISTS mem0 CASCADE')
    op.execute('DROP SCHEMA IF EXISTS shared CASCADE')