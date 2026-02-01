# Identity Admin Service

**Internal-only** administration service for Identity Provider management.

> ⚠️ **Security Notice**: This service MUST be deployed on internal networks only. It should NOT be exposed to the public internet.

## Purpose

The Identity Admin Service provides administrative capabilities for managing:
- OAuth2/OIDC Clients
- User accounts and profiles
- Scopes and API resources
- Audit logs and system settings

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNAL NETWORK                          │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                identity-admin-service                    │   │
│   │                    (Port 8081)                          │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│   │  │ Admin API   │  │ Admin Web   │  │ Health API  │    │   │
│   │  │ /admin/*    │  │ /admin/*    │  │ /health     │    │   │
│   │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                    │
│                              ▼                                    │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    PostgreSQL                             │   │
│   │              (Shared with identity-service)               │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                               │
                     VPN / IP Whitelist
                               │
┌─────────────────────────────────────────────────────────────────┐
│                     ADMIN WORKSTATION                            │
│                    (Authorized Access)                           │
└─────────────────────────────────────────────────────────────────┘
```

## Security Model

### Network Isolation
- **No public ingress**: Service has no LoadBalancer or public-facing Ingress
- **Internal ClusterIP only**: Accessible only within the Kubernetes cluster
- **VPN access**: Administrators connect via VPN to access the internal network
- **IP whitelisting**: Optional additional layer of IP-based restrictions

### Authentication
- Admin-specific authentication (separate from user OAuth)
- Session-based with secure cookies (HttpOnly, Secure, SameSite=Strict)
- MFA required for production environments
- Role-based access control (Super Admin, Client Admin, User Admin)

### Audit
- All administrative actions are logged
- Immutable audit trail for compliance
- Integration with audit-service for centralized logging

## API Endpoints

### Client Management
- `GET /admin/clients` - List clients (paginated)
- `GET /admin/clients/{id}` - Get client details
- `POST /admin/clients` - Create client
- `PATCH /admin/clients/{id}` - Update client
- `DELETE /admin/clients/{id}` - Deactivate client
- `POST /admin/clients/{id}/secrets` - Generate client secret
- `DELETE /admin/clients/{id}/secrets/{secret_id}` - Revoke secret

### User Management
- `GET /admin/users` - List users (paginated)
- `GET /admin/users/{id}` - Get user details
- `POST /admin/users` - Create user
- `PATCH /admin/users/{id}` - Update user
- `DELETE /admin/users/{id}` - Deactivate user
- `POST /admin/users/{id}/activate` - Activate user
- `POST /admin/users/{id}/unlock` - Unlock user
- `POST /admin/users/{id}/reset-password` - Reset password
- `POST /admin/users/{id}/roles` - Add role
- `DELETE /admin/users/{id}/roles/{role}` - Remove role

### Web UI
- `GET /admin` - Dashboard
- `GET /admin/clients` - Clients management page
- `GET /admin/users` - Users management page

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/staging/production) | `development` |
| `APP_PORT` | Service port | `8081` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `IDENTITY_SERVICE_URL` | Identity service internal URL | Required |
| `ADMIN_SESSION_SECRET` | Session encryption key | Required |
| `ADMIN_REQUIRE_MFA` | Require MFA for admin access | `true` |
| `ALLOWED_ADMIN_IPS` | IP whitelist (comma-separated) | `*` |

## Development

```bash
# Install dependencies
cd services/identity-admin-service
uv sync

# Run locally
uv run uvicorn identity_admin_service.main:app --host 0.0.0.0 --port 8081 --reload

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

## Deployment

### Kubernetes (Internal Only)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: identity-admin-service
spec:
  type: ClusterIP  # NO LoadBalancer - internal only!
  ports:
    - port: 8081
      targetPort: 8081
  selector:
    app: identity-admin-service
```

### Docker Compose (Development)

```yaml
identity-admin-service:
  build:
    context: ./services/identity-admin-service
  ports:
    - "8081:8081"  # Bind to localhost only in production
  environment:
    - DATABASE_URL=postgresql://...
    - IDENTITY_SERVICE_URL=http://identity-service:8000
  networks:
    - internal  # Internal network only
```

## Comparison with Industry Standards

| Feature | This Service | Keycloak Admin | Auth0 Dashboard |
|---------|-------------|----------------|-----------------|
| Network Isolation | ✅ Internal only | ✅ Separate console | ✅ Separate domain |
| MFA for Admins | ✅ Required | ✅ Optional | ✅ Required |
| Audit Logging | ✅ All actions | ✅ All actions | ✅ All actions |
| RBAC | ✅ Roles | ✅ Fine-grained | ✅ Teams |
| API Access | ✅ REST | ✅ REST | ✅ REST |

## License

MIT License - See LICENSE file for details.
