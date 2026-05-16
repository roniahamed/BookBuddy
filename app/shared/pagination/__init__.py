"""
Reusable pagination utilities for all modules.
"""
from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel, Field
from fastapi import Query
from sqlalchemy.orm import Query as SAQuery
import math

T = TypeVar("T")


class PaginationParams:
    """FastAPI dependency for pagination query params."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number (1-indexed)"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    ):
        self.page = page
        self.per_page = per_page
        self.offset = (page - 1) * per_page


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: List = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    pages: int = 0
    has_next: bool = False
    has_prev: bool = False


def paginate(query: SAQuery, params: PaginationParams) -> dict:
    """
    Apply pagination to a SQLAlchemy query and return response dict.
    
    Returns dict with keys: items, total, page, per_page, pages, has_next, has_prev
    """
    total = query.count()
    pages = math.ceil(total / params.per_page) if params.per_page > 0 else 0
    items = query.offset(params.offset).limit(params.per_page).all()

    return {
        "items": items,
        "total": total,
        "page": params.page,
        "per_page": params.per_page,
        "pages": pages,
        "has_next": params.page < pages,
        "has_prev": params.page > 1,
    }
