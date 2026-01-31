# FastMicro Architecture Overview

## System Architecture

```
                                    ┌─────────────────────────────────────────────────────────────┐
                                    │                        Clients                               │
                                    │              (Web Browser, Mobile Apps, CLI)                 │
                                    └─────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          TRAEFIK                                                      │
│                                    (API Gateway / Load Balancer)                                      │
│                         ┌────────────────────────────────────────────────────┐                        │
│                         │  Routes:                                            │                        │
│                         │  • app.localhost       → webshell-service:3000     │                        │
│                         │  • api.localhost/audit → audit-service:8000        │                        │
│                         │  • api.localhost/meta  → metastore-service:8000    │                        │
│                         └────────────────────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
         │                         │                              │                          │
         ▼                         ▼                              ▼                          ▼
┌─────────────────┐     ┌──────────────────┐          ┌───────────────────┐     ┌───────────────────┐
│   WebShell      │     │  Federation      │          │   Audit           │     │   Metastore       │
│   Service       │     │  Gateway         │          │   Service         │     │   Service         │
│                 │     │                  │          │                   │     │                   │
│  Next.js 15     │     │  FastAPI         │          │  FastAPI          │     │  FastAPI          │
│  React 19       │     │  GraphQL Fed     │          │  Clean Arch       │     │  Clean Arch       │
│  TypeScript     │     │  Clean Arch      │          │  Shared Lib       │     │  Shared Lib       │
│                 │     │                  │          │                   │     │                   │
│  Port: 3000     │     │  Port: 8000      │          │  Port: 8001       │     │  Port: 8002       │
└─────────────────┘     └──────────────────┘          └───────────────────┘     └───────────────────┘
                                                              │                          │
                                                              └──────────┬───────────────┘
                                                                         │
                                                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     SHARED LIBRARY                                                   │
│                                                                                                      │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│   │  auth   │  │   dbs   │  │  excep  │  │  utils  │  │  http   │  │  proto  │  │  const  │        │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    INFRASTRUCTURE                                                    │
│                                                                                                      │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐         │
│   │ PostgreSQL│  │  MongoDB  │  │   Redis   │  │ RabbitMQ  │  │  Keycloak │  │   Vault   │         │
│   │           │  │           │  │           │  │           │  │           │  │           │         │
│   │ Port:5432 │  │ Port:27017│  │ Port:6379 │  │ Port:5672 │  │ Port:8180 │  │ Port:8200 │         │
│   └───────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    OBSERVABILITY                                                     │
│                                                                                                      │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐                                        │
│   │Prometheus │  │  Grafana  │  │  Jaeger   │  │    Seq    │                                        │
│   │  Metrics  │  │Dashboards │  │  Tracing  │  │  Logging  │                                        │
│   │           │  │           │  │           │  │           │                                        │
│   │ Port:9090 │  │ Port:3001 │  │ Port:16686│  │ Port:5341 │                                        │
│   └───────────┘  └───────────┘  └───────────┘  └───────────┘                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Service Architecture (Clean Architecture)

Each Python microservice follows Clean Architecture:

```
┌──────────────────────────────────────────────────────────────────┐
│                         API Layer                                 │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Routes (Controllers)                               │  │
│  │  • Health endpoints (/health, /ready, /metrics)            │  │
│  │  • Domain endpoints (/api/v1/...)                          │  │
│  │  • Request/Response DTOs                                    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Application Layer                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Application Services (Use Cases)                           │  │
│  │  • Business workflow orchestration                          │  │
│  │  • Transaction management                                   │  │
│  │  • Domain event publishing                                  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Domain Layer                                 │
│  ┌───────────────────────┐  ┌───────────────────────────────┐   │
│  │      Entities         │  │    Repository Interfaces      │   │
│  │  • Business objects   │  │    (Ports/Abstractions)       │   │
│  │  • Value objects      │  │  • IAuditRepository           │   │
│  │  • Domain events      │  │  • IMetadataRepository        │   │
│  └───────────────────────┘  └───────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐    │
│  │  Middleware │  │ Persistence │  │   External Services   │    │
│  │  • Logging  │  │ • MongoDB   │  │   • Keycloak client   │    │
│  │  • RequestID│  │ • PostgreSQL│  │   • RabbitMQ client   │    │
│  │  • Auth     │  │ • Redis     │  │   • HTTP clients      │    │
│  └─────────────┘  └─────────────┘  └───────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Request → Traefik → Service API → Application Service → Domain → Infrastructure
                                                                       │
Response ← Traefik ← Service API ← Application Service ← Domain ←──────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js 15, React 19, TypeScript | Web application |
| API Gateway | Traefik 3.x | Routing, load balancing, TLS |
| Backend | FastAPI, Python 3.12+ | Microservices |
| Shared Code | Poetry monorepo | Common utilities |
| Auth | Keycloak 24+ | Identity & access management |
| Databases | PostgreSQL 17, MongoDB 7 | Data persistence |
| Caching | Redis 8 | Session, caching |
| Messaging | RabbitMQ 4 | Async communication |
| Secrets | HashiCorp Vault | Secret management |
| Metrics | Prometheus + Grafana | Monitoring |
| Logging | Seq | Centralized logging |
| Tracing | Jaeger | Distributed tracing |
| CI/CD | GitHub Actions | Automation |
| Containers | Docker, Docker Compose | Containerization |

## Key Design Decisions

1. **Clean Architecture**: Separation of concerns, testability
2. **Shared Library**: DRY principle, consistency
3. **API Versioning**: `/api/v1/` prefix for all endpoints
4. **Health Checks**: `/health`, `/ready`, `/metrics` on all services
5. **Structured Logging**: JSON format, correlation IDs
6. **OpenTelemetry**: Standard for observability

## See Also

- [Integration Guide](./integration-guide.md)
- [ADR Index](./adr/README.md)
