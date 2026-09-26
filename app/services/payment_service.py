import uuid
import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus, WebhookEvent
from app.models.user import User


def process_simulated_payment(
    db: Session,
    user: User,
    booking_id: int,
    simulate: str = "SUCCESS",
    idempotency_key: str | None = None,
) -> Payment:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if not user.is_admin and booking.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay for this booking")

    # 1. Check idempotency FIRST
    if idempotency_key:
        existing = db.query(Payment).filter(Payment.idempotency_key == idempotency_key).first()
        if existing:
            if existing.booking_id != booking.id:
                raise HTTPException(status_code=409, detail="Idempotency key belongs to another booking")
            return existing

    # 2. Check if booking is in payable state
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=409, detail="Booking is not payable in its current state")

    if booking.payment:
        raise HTTPException(status_code=409, detail="A payment already exists for this booking")

    if not idempotency_key:
        idempotency_key = f"auto_{uuid.uuid4().hex}"

    payment_status = PaymentStatus.SUCCESS if simulate == "SUCCESS" else PaymentStatus.FAILED
    payment = Payment(
        booking_id=booking.id,
        provider_payment_id=f"sim_{uuid.uuid4().hex}",
        amount=booking.amount,
        status=payment_status,
        idempotency_key=idempotency_key,
    )
    booking.status = (
        BookingStatus.CONFIRMED
        if payment_status == PaymentStatus.SUCCESS
        else BookingStatus.FAILED
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def process_webhook(
    db: Session,
    event_id: str,
    provider_payment_id: str | None = None,
    booking_id: int | None = None,
    status_value: str = "SUCCESS",
    raw_payload: dict | None = None,
) -> Payment:
    # 1. Check if this exact event_id was already processed (Idempotency)
    existing_event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if existing_event:
        existing_event.retry_count += 1
        db.commit()
        if existing_event.provider_payment_id:
            payment = (
                db.query(Payment)
                .filter(Payment.provider_payment_id == existing_event.provider_payment_id)
                .first()
            )
            if payment:
                return payment
        if existing_event.booking_id:
            payment = db.query(Payment).filter(Payment.booking_id == existing_event.booking_id).first()
            if payment:
                return payment

    existing_payment_by_event = (
        db.query(Payment).filter(Payment.provider_event_id == event_id).first()
    )
    if existing_payment_by_event:
        return existing_payment_by_event

    # 2. Find payment by provider_payment_id or booking_id
    payment = None
    if provider_payment_id:
        payment = (
            db.query(Payment)
            .filter(Payment.provider_payment_id == provider_payment_id)
            .first()
        )

    if not payment and booking_id:
        payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()

    # 3. If no payment exists yet, check if valid booking exists
    if not payment:
        if booking_id:
            booking = db.get(Booking, booking_id)
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            if booking.status == BookingStatus.CANCELLED:
                raise HTTPException(status_code=409, detail="Cannot process payment for a cancelled booking")

            target_status = (
                PaymentStatus.SUCCESS if status_value == "SUCCESS" else PaymentStatus.FAILED
            )
            payment = Payment(
                booking_id=booking.id,
                provider_payment_id=provider_payment_id or f"wh_{uuid.uuid4().hex}",
                provider_event_id=event_id,
                amount=booking.amount,
                status=target_status,
            )
            booking.status = (
                BookingStatus.CONFIRMED if target_status == PaymentStatus.SUCCESS else BookingStatus.FAILED
            )
            db.add(payment)
            webhook_record = WebhookEvent(
                event_id=event_id,
                provider_payment_id=payment.provider_payment_id,
                booking_id=booking.id,
                status=status_value,
                payload=json.dumps(raw_payload) if raw_payload else None,
            )
            db.add(webhook_record)
            db.commit()
            db.refresh(payment)
            return payment
        else:
            raise HTTPException(status_code=404, detail="Payment not found")

    # 4. Process existing payment
    booking = payment.booking
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(
            status_code=409,
            detail="Cannot process payment for a cancelled booking",
        )

    # Protect against corrupting confirmed booking
    if payment.status == PaymentStatus.SUCCESS and status_value == "FAILED":
        raise HTTPException(
            status_code=409,
            detail="Cannot modify already confirmed payment to failed",
        )

    target_status = (
        PaymentStatus.SUCCESS if status_value == "SUCCESS" else PaymentStatus.FAILED
    )

    payment.status = target_status
    payment.provider_event_id = event_id

    if target_status == PaymentStatus.SUCCESS:
        booking.status = BookingStatus.CONFIRMED
    else:
        booking.status = BookingStatus.FAILED

    webhook_record = WebhookEvent(
        event_id=event_id,
        provider_payment_id=payment.provider_payment_id,
        booking_id=booking.id,
        status=status_value,
        payload=json.dumps(raw_payload) if raw_payload else None,
    )
    db.add(webhook_record)
    db.commit()
    db.refresh(payment)
    return payment
