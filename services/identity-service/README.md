# Identity Service

Enterprise Identity Provider implementing OAuth 2.0 and OpenID Connect standards.

## Overview

The Identity Service is a Python-based Identity Provider (IdP) built with FastAPI and Authlib, providing authentication and authorization services equivalent to Microsoft Identity Platform or Duende IdentityServer.

## Features

### OAuth 2.0 / OpenID Connect
- Authorization Code Grant with PKCE
- Client Credentials Grant
- Refresh Token Grant
- Token Introspection (RFC 7662)
- Token Revocation (RFC 7009)
- Dynamic Client Registration (RFC 7591)

### Security
- JWT Access Tokens (RS256)
- Secure Password Hashing (bcrypt)
- Multi-Factor Authentication (TOTP)
- Rate Limiting
- Brute Force Protection

### Standards Compliance
- OAuth 2.0 (RFC 6749)
- OpenID Connect Core 1.0
- PKCE (RFC 7636)
- JWT (RFC 7519)
- JWKS (RFC 7517)

## Architecture

```
src/identity_service/
├── api/                    # Presentation Layer
│   ├── oauth/              # OAuth2/OIDC endpoints
│   └── web/                # Login UI pages
├── application/            # Use Cases
│   └── services/
├── domain/                 # Business Logic
│   ├── entities/
│   ├── value_objects/
│   └── repositories/
├── infrastructure/         # External Adapters
│   ├── oauth/              # Authlib integration
│   ├── persistence/
│   └── security/
└── configs/
```

## Getting Started

```bash
cd services/identity-service
poetry install
poetry run uvicorn identity_service.main:app --reload --port 8003
```

## Endpoints

### OAuth 2.0 / OIDC

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/openid-configuration` | GET | Discovery document |
| `/.well-known/jwks.json` | GET | Public signing keys |
| `/oauth2/authorize` | GET | Authorization endpoint |
| `/oauth2/token` | POST | Token exchange |
| `/oauth2/revoke` | POST | Token revocation |
| `/oauth2/introspect` | POST | Token introspection |
| `/oauth2/userinfo` | GET | User claims |

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |
| `/metrics` | GET | Prometheus metrics |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | development | Environment |
| `DATABASE_URL` | - | PostgreSQL connection |
| `REDIS_URL` | - | Redis connection |
| `JWT_ISSUER` | - | Token issuer URL |
| `JWT_ALGORITHM` | RS256 | Signing algorithm |
| `ACCESS_TOKEN_LIFETIME` | 3600 | Token lifetime (seconds) |

## License

MIT License
