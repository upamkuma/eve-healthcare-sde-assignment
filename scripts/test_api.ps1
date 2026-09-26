$baseUrl = "http://localhost:8000"
Write-Host "Health:"
Invoke-RestMethod "$baseUrl/health"
Write-Host "Swagger: $baseUrl/docs"
