"""
Books module filters — reusable filter/sort classes for Browse Book screen.
"""
from fastapi import Query
from typing import Optional


class BookFilters:
    """
    FastAPI dependency for book filtering.
    Maps to the Browse Book screen filter chips and category tabs.
    """

    def __init__(
        self,
        search: Optional[str] = Query(None, description="Search by title, author, or genre name"),
        genre_id: Optional[int] = Query(None, description="Filter by genre ID (category tabs)"),
        condition: Optional[str] = Query(None, description="Filter by condition: New | Good | Used"),
        availability: Optional[str] = Query(None, description="Filter by availability: available | borrowed"),
        sort_by: Optional[str] = Query(
            "newest",
            description="Sort: newest | top_rated | nearby | title_asc | title_desc",
        ),
        # Location params for "Nearby" and "Books Near You"
        user_lat: Optional[float] = Query(None, description="User latitude for distance calculation"),
        user_lon: Optional[float] = Query(None, description="User longitude for distance calculation"),
        radius_km: Optional[float] = Query(None, description="Max distance in km (for Nearby filter)"),
    ):
        self.search = search
        self.genre_id = genre_id
        self.condition = condition
        self.availability = availability
        self.sort_by = sort_by
        self.user_lat = user_lat
        self.user_lon = user_lon
        self.radius_km = radius_km
