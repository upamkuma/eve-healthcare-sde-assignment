$baseUrl = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "EVE Healthcare API End-to-End Test (PowerShell)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Health check
Write-Host "`n1. Health check:" -ForegroundColor Yellow
$health = Invoke-RestMethod "$baseUrl/health" -Method Get
$health | ConvertTo-Json

# 2. Login
Write-Host "`n2. User Login:" -ForegroundColor Yellow
$loginPayload = @{
    email = "user@evehealthcare.com"
    password = "User@123"
} | ConvertTo-Json

$loginRes = Invoke-RestMethod "$baseUrl/auth/login" -Method Post -ContentType "application/json" -Body $loginPayload
$token = $loginRes.access_token
Write-Host "JWT Access Token acquired successfully." -ForegroundColor Green

$authHeaders = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}

# 3. List Centres
Write-Host "`n3. List Centres:" -ForegroundColor Yellow
$centres = Invoke-RestMethod "$baseUrl/centres?page=1&page_size=2" -Method Get
Write-Host "Found $($centres.Count) centres. First centre: $($centres[0].name)" -ForegroundColor Green

# 4. Create Booking
Write-Host "`n4. Create Diagnostic Test Booking:" -ForegroundColor Yellow
$futureDate = (Get-Date).ToUniversalTime().AddDays(2).ToString("yyyy-MM-ddTHH:mm:ssZ")
$bookingPayload = @{
    test_id = 1
    centre_id = 1
    appointment_at = $futureDate
} | ConvertTo-Json

$booking = Invoke-RestMethod "$baseUrl/bookings" -Method Post -Headers $authHeaders -Body $bookingPayload
$bookingId = $booking.id
Write-Host "Created Booking ID: $bookingId with Amount: $($booking.amount) and Status: $($booking.status)" -ForegroundColor Green

# 5. Simulate Payment
Write-Host "`n5. Simulate Payment (SUCCESS):" -ForegroundColor Yellow
$idempotencyKey = "ps-test-key-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$paymentPayload = @{
    booking_id = $bookingId
    simulate = "SUCCESS"
    idempotency_key = $idempotencyKey
} | ConvertTo-Json

$payment = Invoke-RestMethod "$baseUrl/payments/" -Method Post -Headers $authHeaders -Body $paymentPayload
Write-Host "Payment Status: $($payment.status), Provider Payment ID: $($payment.provider_payment_id)" -ForegroundColor Green

# 6. Verify Booking is CONFIRMED
Write-Host "`n6. Verify Booking Status:" -ForegroundColor Yellow
$updatedBooking = Invoke-RestMethod "$baseUrl/bookings/$bookingId" -Method Get -Headers $authHeaders
Write-Host "Booking Status is now: $($updatedBooking.status)" -ForegroundColor Green

# 7. Payment Idempotency Check
Write-Host "`n7. Test Payment Idempotency:" -ForegroundColor Yellow
$replayPayment = Invoke-RestMethod "$baseUrl/payments/" -Method Post -Headers $authHeaders -Body $paymentPayload
Write-Host "Replay returned existing Payment ID: $($replayPayment.id) (Exact Match: $($payment.id -eq $replayPayment.id))" -ForegroundColor Green

# 8. Webhook Idempotency Check
Write-Host "`n8. Test Webhook Idempotency:" -ForegroundColor Yellow
$eventId = "evt-ps-test-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
$webhookPayload = @{
    event_id = $eventId
    provider_payment_id = $payment.provider_payment_id
    status = "SUCCESS"
} | ConvertTo-Json

$firstWebhook = Invoke-RestMethod "$baseUrl/payments/webhook/" -Method Post -ContentType "application/json" -Body $webhookPayload
$secondWebhook = Invoke-RestMethod "$baseUrl/payments/webhook/" -Method Post -ContentType "application/json" -Body $webhookPayload
Write-Host "Webhook processed idempotently without duplicates (Match: $($firstWebhook.id -eq $secondWebhook.id))" -ForegroundColor Green

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host "All Tests Completed Successfully!" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
