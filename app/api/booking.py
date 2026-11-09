from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.dependencies import CurrentUser, get_booking_service
from app.models.user import Appointment, AppointmentStatus, LawyerAvailability, User, UserRole
from app.schemas.booking import (
    AppointmentCreate,
    AppointmentResponse,
    AvailabilityCreate,
    AvailabilityResponse,
    AvailabilityUpdate,
)
from app.services.booking_service import (
    BookingConflictError,
    BookingNotFoundError,
    BookingPermissionError,
    BookingService,
    BookingValidationError,
)

router = APIRouter(tags=["Appointments and Availability"])
Booking = Annotated[BookingService, Depends(get_booking_service)]


def ensure_role(user: User, role: UserRole) -> None:
    if user.role != role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{role.value.title()} role required",
        )


def booking_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, BookingNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, BookingPermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, BookingConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, BookingValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Booking request could not be completed",
    )


@router.post(
    "/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability(
    payload: AvailabilityCreate,
    user: CurrentUser,
    service: Booking,
) -> LawyerAvailability:
    ensure_role(user, UserRole.LAWYER)
    try:
        return service.create_availability(user, payload.model_dump())
    except (BookingConflictError, BookingValidationError) as exc:
        raise booking_http_error(exc) from exc


@router.get("/availability/me", response_model=list[AvailabilityResponse])
def get_my_availability(user: CurrentUser, service: Booking) -> list[LawyerAvailability]:
    ensure_role(user, UserRole.LAWYER)
    return service.list_my_availability(user.id)


@router.put(
    "/availability/{availability_id}",
    response_model=AvailabilityResponse,
)
def update_availability(
    availability_id: UUID,
    payload: AvailabilityUpdate,
    user: CurrentUser,
    service: Booking,
) -> LawyerAvailability:
    ensure_role(user, UserRole.LAWYER)
    try:
        return service.update_availability(
            user,
            availability_id,
            payload.model_dump(exclude_unset=True),
        )
    except (BookingNotFoundError, BookingPermissionError, BookingConflictError, BookingValidationError) as exc:
        raise booking_http_error(exc) from exc


@router.delete(
    "/availability/{availability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_availability(
    availability_id: UUID,
    user: CurrentUser,
    service: Booking,
) -> Response:
    ensure_role(user, UserRole.LAWYER)
    try:
        service.delete_availability(user, availability_id)
    except (BookingNotFoundError, BookingPermissionError) as exc:
        raise booking_http_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment(
    payload: AppointmentCreate,
    user: CurrentUser,
    service: Booking,
) -> Appointment:
    ensure_role(user, UserRole.CLIENT)
    try:
        return service.create_appointment(user, payload.model_dump())
    except (
        BookingConflictError,
        BookingNotFoundError,
        BookingPermissionError,
        BookingValidationError,
    ) as exc:
        raise booking_http_error(exc) from exc


@router.get("/appointments/my", response_model=list[AppointmentResponse])
def get_my_appointments(user: CurrentUser, service: Booking) -> list[Appointment]:
    ensure_role(user, UserRole.CLIENT)
    return service.list_for_client(user.id)


@router.get("/appointments/lawyer", response_model=list[AppointmentResponse])
def get_lawyer_appointments(user: CurrentUser, service: Booking) -> list[Appointment]:
    ensure_role(user, UserRole.LAWYER)
    return service.list_for_lawyer(user.id)


def change_status(
    appointment_id: UUID,
    user: User,
    service: BookingService,
    target: AppointmentStatus,
) -> Appointment:
    try:
        return service.transition(user, appointment_id, target)
    except (
        BookingConflictError,
        BookingNotFoundError,
        BookingPermissionError,
        BookingValidationError,
    ) as exc:
        raise booking_http_error(exc) from exc


@router.put("/appointments/{appointment_id}/approve", response_model=AppointmentResponse)
def approve_appointment(
    appointment_id: UUID,
    user: CurrentUser,
    service: Booking,
) -> Appointment:
    ensure_role(user, UserRole.LAWYER)
    return change_status(appointment_id, user, service, AppointmentStatus.APPROVED)


@router.put("/appointments/{appointment_id}/reject", response_model=AppointmentResponse)
def reject_appointment(
    appointment_id: UUID,
    user: CurrentUser,
    service: Booking,
) -> Appointment:
    ensure_role(user, UserRole.LAWYER)
    return change_status(appointment_id, user, service, AppointmentStatus.REJECTED)


@router.put("/appointments/{appointment_id}/complete", response_model=AppointmentResponse)
def complete_appointment(
    appointment_id: UUID,
    user: CurrentUser,
    service: Booking,
) -> Appointment:
    ensure_role(user, UserRole.LAWYER)
    return change_status(appointment_id, user, service, AppointmentStatus.COMPLETED)


@router.put("/appointments/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: UUID,
    user: CurrentUser,
    service: Booking,
) -> Appointment:
    ensure_role(user, UserRole.CLIENT)
    return change_status(appointment_id, user, service, AppointmentStatus.CANCELLED)
