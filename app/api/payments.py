from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.rate_limit import payment_rate_limiter
from app.db.session import get_db
from app.models.booking import Booking
from app.models.payment import Payment, WebhookEvent
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentWebhook
from app.services.payment_service import process_simulated_payment, process_webhook

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    request: Request,
    payload: PaymentCreate,
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment_rate_limiter(request)
    effective_idempotency_key = payload.idempotency_key or idempotency_key_header

    return process_simulated_payment(
        db=db,
        user=current_user,
        booking_id=payload.booking_id,
        simulate=payload.simulate,
        idempotency_key=effective_idempotency_key,
    )


@router.post("/webhook", response_model=PaymentResponse, include_in_schema=False)
@router.post("/webhook/", response_model=PaymentResponse)
def payment_webhook(
    payload: PaymentWebhook,
    db: Session = Depends(get_db),
):
    return process_webhook(
        db=db,
        event_id=payload.event_id,
        provider_payment_id=payload.provider_payment_id,
        booking_id=payload.booking_id,
        status_value=payload.status,
        raw_payload=payload.model_dump(),
    )


@router.get("/booking/{booking_id}", response_model=PaymentResponse)
def get_payment_for_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if not current_user.is_admin and booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view payment for this booking")

    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="No payment found for this booking")

    return payment


@router.get("/webhook/events")
def list_webhook_events(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    events = db.query(WebhookEvent).order_by(WebhookEvent.id.desc()).limit(50).all()
    return [
        {
            "id": e.id,
            "event_id": e.event_id,
            "provider_payment_id": e.provider_payment_id,
            "booking_id": e.booking_id,
            "status": e.status,
            "retry_count": e.retry_count,
            "processed_at": e.processed_at.isoformat() if e.processed_at else None,
        }
        for e in events
    ]
