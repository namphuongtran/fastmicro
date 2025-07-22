#!/bin/bash
set -e  # Exit on any error

# Install OpenSSL if not present
if ! command -v openssl &> /dev/null; then
    echo "Installing OpenSSL..."
    apk add --no-cache openssl
fi

# Wait for the cert directory to be mounted
echo "Waiting for certificate directory..."
while [ ! -d "/certs" ]; do
    sleep 1
done

# Generate self-signed certificate if it doesn't exist
if [ ! -f "/certs/local.ags.com.crt" ]; then
    echo "Generating self-signed certificate..."
    
    if openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /certs/local.ags.com.key \
        -out /certs/local.ags.com.crt \
        -subj "/CN=local.ags.com" \
        -addext "subjectAltName=DNS:auth.local.ags.com,DNS:app.local.ags.com,DNS:local.ags.com,DNS:app.local.ags.com"; then
        
        # Set appropriate permissions
        chmod 644 /certs/local.ags.com.crt
        chmod 600 /certs/local.ags.com.key
        
        echo "Certificate generated successfully"
    else
        echo "Failed to generate certificate" >&2
        exit 1
    fi
else
    echo "Certificate already exists"
fi

# Keep container running
echo "Certificate service running..."
while true; do
    sleep 3600
done