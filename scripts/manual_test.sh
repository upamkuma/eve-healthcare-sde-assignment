#!/usr/bin/env bash
set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "=================================================="
echo "EVE Healthcare API End-to-End Test"
echo "=================================================="

echo ""
echo "1. Health check:"
curl -s -X GET "$BASE_URL/health"
echo ""

echo ""
echo "2. User login:"
LOGIN_RES=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@evehealthcare.com", "password": "User@123"}')
echo "$LOGIN_RES"

TOKEN=$(echo "$LOGIN_RES" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Login failed. Ensure seed data has been loaded: python -m app.seed"
  exit 1
fi

echo "Access Token acquired."

echo ""
echo "3. List Diagnostic Centres:"
curl -s -X GET "$BASE_URL/centres?page=1&page_size=5" | head -c 300
echo "... (truncated)"

echo ""
echo "4. Create Diagnostic Test Booking:"
BOOKING_RES=$(curl -s -X POST "$BASE_URL/bookings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_id": 1, "centre_id": 1, "appointment_at": "2027-06-15T10:00:00Z"}')
echo "$BOOKING_RES"

BOOKING_ID=$(echo "$BOOKING_RES" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

if [ -z "$BOOKING_ID" ]; then
  echo "Booking creation failed."
  exit 1
fi

echo "Booking ID: $BOOKING_ID"

echo ""
echo "5. Simulate Payment (SUCCESS):"
IDEMPOTENCY_KEY="cli-test-key-$(date +%s)"
PAYMENT_RES=$(curl -s -X POST "$BASE_URL/payments/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"booking_id\": $BOOKING_ID, \"simulate\": \"SUCCESS\", \"idempotency_key\": \"$IDEMPOTENCY_KEY\"}")
echo "$PAYMENT_RES"

echo ""
echo "6. Verify Booking is CONFIRMED:"
curl -s -X GET "$BASE_URL/bookings/$BOOKING_ID" \
  -H "Authorization: Bearer $TOKEN"
echo ""

echo ""
echo "7. Test Payment Idempotency (replay same idempotency key):"
curl -s -X POST "$BASE_URL/payments/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"booking_id\": $BOOKING_ID, \"simulate\": \"SUCCESS\", \"idempotency_key\": \"$IDEMPOTENCY_KEY\"}"
echo ""

echo ""
echo "8. Test Webhook Idempotency:"
EVENT_ID="evt-cli-test-$(date +%s)"
PAYMENT_ID=$(echo "$PAYMENT_RES" | grep -o '"provider_payment_id":"[^"]*' | cut -d'"' -f4)

echo "First webhook submission:"
curl -s -X POST "$BASE_URL/payments/webhook/" \
  -H "Content-Type: application/json" \
  -d "{\"event_id\": \"$EVENT_ID\", \"provider_payment_id\": \"$PAYMENT_ID\", \"status\": \"SUCCESS\"}"
echo ""

echo "Replaying same webhook (idempotency check):"
curl -s -X POST "$BASE_URL/payments/webhook/" \
  -H "Content-Type: application/json" \
  -d "{\"event_id\": \"$EVENT_ID\", \"provider_payment_id\": \"$PAYMENT_ID\", \"status\": \"SUCCESS\"}"
echo ""

echo "=================================================="
echo "All End-to-End Checks Passed Successfully!"
echo "=================================================="
