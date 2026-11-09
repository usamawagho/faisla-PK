from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_lawyer_profile_service
from app.models.user import LawyerProfile, VerificationStatus
from app.schemas.lawyer_profile import LawyerMarketplaceResponse
from app.services.lawyer_profile_service import (
    LawyerProfileNotFoundError,
    LawyerProfileService,
)

router = APIRouter(prefix="/lawyers", tags=["Lawyer Marketplace"])
MarketplaceService = Annotated[
    LawyerProfileService,
    Depends(get_lawyer_profile_service),
]


@router.get("", response_model=list[LawyerMarketplaceResponse])
def search_lawyers(
    service: MarketplaceService,
    city: str | None = Query(default=None, min_length=1, max_length=100),
    preferred_city: str | None = Query(default=None, min_length=1, max_length=100),
    specialization: str | None = Query(default=None, min_length=1, max_length=200),
    min_years_experience: int | None = Query(default=None, ge=0, le=80),
    max_years_experience: int | None = Query(default=None, ge=0, le=80),
    verification_status: VerificationStatus | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[LawyerProfile]:
    if (
        min_years_experience is not None
        and max_years_experience is not None
        and min_years_experience > max_years_experience
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_years_experience cannot exceed max_years_experience",
        )
    return service.search_public(
        city=city,
        preferred_city=preferred_city,
        specialization=specialization,
        min_years_experience=min_years_experience,
        max_years_experience=max_years_experience,
        verification_status=verification_status,
        offset=offset,
        limit=limit,
    )


@router.get("/{profile_id}", response_model=LawyerMarketplaceResponse)
def get_lawyer(
    profile_id: int,
    service: MarketplaceService,
) -> LawyerProfile:
    try:
        return service.get_public(profile_id)
    except LawyerProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lawyer not found",
        ) from exc
