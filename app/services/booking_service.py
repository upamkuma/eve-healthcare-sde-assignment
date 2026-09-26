from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.diagnostic import DiagnosticCentre, DiagnosticTest
from app.models.user import User


def create_booking(
    db: Session,
    user: User,
    test_id: int,
    centre_id: int,
    appointment_at: datetime,
) -> Booking:
    if appointment_at.tzinfo is None:
        appointment_at = appointment_at.replace(tzinfo=timezone.utc)

    if appointment_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment must be in the future",
        )

    test = db.get(DiagnosticTest, test_id)
    centre = db.get(DiagnosticCentre, centre_id)

    if not test or not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic test or centre not found",
        )

    if test.centre_id != centre.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected test does not belong to the selected centre",
        )

    booking = Booking(
        user_id=user.id,
        test_id=test.id,
        centre_id=centre.id,
        appointment_at=appointment_at,
        amount=test.price,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
