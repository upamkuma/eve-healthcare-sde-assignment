from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.booking import Booking, BookingStatus
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.booking_service import create_booking

router = APIRouter(prefix="/bookings", tags=["Bookings"])


def get_owned_booking(booking_id: int, user: User, db: Session) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if not user.is_admin and booking.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this booking")
    return booking


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_booking(
        db=db,
        user=current_user,
        test_id=payload.test_id,
        centre_id=payload.centre_id,
        appointment_at=payload.appointment_at,
    )


@router.get("", response_model=list[BookingResponse])
def list_bookings(
    status: BookingStatus | None = Query(default=None, description="Filter by booking status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    all_users: bool = Query(default=False, description="Admin only: view all users' bookings"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Booking)

    if not (current_user.is_admin and all_users):
        query = query.filter(Booking.user_id == current_user.id)

    if status:
        query = query.filter(Booking.status == status)

    offset = (page - 1) * page_size
    return query.order_by(Booking.id.desc()).offset(offset).limit(page_size).all()


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_owned_booking(booking_id, current_user, db)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = get_owned_booking(booking_id, current_user, db)

    if booking.status != BookingStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail="Only pending bookings can be cancelled",
        )

    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking
