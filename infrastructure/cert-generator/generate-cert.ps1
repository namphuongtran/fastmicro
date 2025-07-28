#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

# Install OpenSSL if not present
if (-not (Get-Command openssl -ErrorAction SilentlyContinue)) {
    Write-Host "Installing OpenSSL..."
    apk add --no-cache openssl
}

# Wait for the cert directory to be mounted
Write-Host "Waiting for certificate directory..."
while (-not (Test-Path "/certs")) {
    Start-Sleep -Seconds 1
}

# Generate self-signed certificate if it doesn't exist
if (-not (Test-Path "/certs/local.ags.com.crt")) {
    Write-Host "Generating self-signed certificate..."
    try {
        & openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
        -keyout /certs/local.ags.com.key `
        -out /certs/local.ags.com.crt `
        -subj "/CN=local.ags.com" `
        -addext "subjectAltName=DNS:auth.local.ags.com,DNS:app.local.ags.com,DNS:local.ags.com,DNS:app.local.ags.com"

        # Set appropriate permissions
        chmod 644 /certs/local.ags.com.crt
        chmod 600 /certs/local.ags.com.key

        Write-Host "Certificate generated successfully"
    }
    catch {
        Write-Error "Failed to generate certificate: $_"
        exit 1
    }
}
else {
    Write-Host "Certificate already exists"
}

# Keep container running
Write-Host "Certificate service running..."
while ($true) {
    Start-Sleep -Seconds 3600
}
