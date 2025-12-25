"""Initial migration with all tables

Revision ID: 001
Revises: 
Create Date: 2024-12-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (should already be enabled, but just in case)
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_hash', sa.String(128), nullable=False),
        sa.Column('key_prefix', sa.String(8), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_email', sa.String(255), nullable=True),
        sa.Column('quota_total', sa.Integer(), nullable=False, default=10000),
        sa.Column('quota_used', sa.Integer(), nullable=False, default=0),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, default=60),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    
    # Create web_pages table
    op.create_table(
        'web_pages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('markdown', sa.Text(), nullable=True),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('published_date', sa.DateTime(), nullable=True),
        sa.Column('language', sa.String(10), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('crawled_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url')
    )
    op.create_index('ix_web_pages_domain', 'web_pages', ['domain'])
    op.create_index('ix_web_pages_domain_crawled', 'web_pages', ['domain', 'crawled_at'])
    
    # Create page_chunks table with vector column
    op.create_table(
        'page_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('start_char', sa.Integer(), nullable=True),
        sa.Column('end_char', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['page_id'], ['web_pages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_page_chunks_page_id', 'page_chunks', ['page_id'])
    
    # Create crawl_jobs table
    op.create_table(
        'crawl_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seed_url', sa.Text(), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('max_pages', sa.Integer(), nullable=False, default=100),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('pages_crawled', sa.Integer(), nullable=False, default=0),
        sa.Column('pages_indexed', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create search_queries table
    op.create_table(
        'search_queries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('num_results', sa.Integer(), nullable=False, default=10),
        sa.Column('filters', sa.Text(), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=False, default=0),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('search_queries')
    op.drop_table('crawl_jobs')
    op.drop_table('page_chunks')
    op.drop_index('ix_web_pages_domain_crawled', table_name='web_pages')
    op.drop_index('ix_web_pages_domain', table_name='web_pages')
    op.drop_table('web_pages')
    op.drop_table('api_keys')
