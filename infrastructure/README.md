# Infrastructure

This directory contains all infrastructure-as-code, deployment configurations, and DevOps tooling.

## Directory Structure

```
infrastructure/
├── cert-generator/     # SSL/TLS certificate generation scripts
├── k8s/               # Kubernetes manifests and Helm charts
│   └── helm-charts/   # Helm charts for services
├── monitoring/        # Observability stack configurations
│   ├── grafana/       # Grafana dashboards and provisioning
│   └── prometheus/    # Prometheus configuration
├── pipelines/         # CI/CD pipeline configurations
├── scripts/           # Deployment and setup scripts
├── terraform/         # Infrastructure provisioning (IaC)
└── traefik/           # Traefik reverse proxy configuration
```

## Components

### Monitoring

Observability stack for local development and production:

| Tool | Purpose | Port |
|------|---------|------|
| Prometheus | Metrics collection | 9090 |
| Grafana | Visualization | 3001 |

**Usage with Docker Compose:**
```bash
docker compose -f docker-compose.dev.yml up prometheus grafana
```

### Kubernetes

Helm charts for deploying services to Kubernetes:

- `helm-charts/keycloak/` - Identity provider
- `helm-charts/postgres/` - PostgreSQL database
- `helm-charts/mssql/` - SQL Server (optional)

### Scripts

Setup and deployment automation:

- `1-prerequisites/` - Install required tools (Poetry, Helm, kubectl)
- `2-deployment/` - Service deployment scripts

### Traefik

Local reverse proxy configuration for routing:
- Routes `*.localhost` domains to services
- TLS termination for local development

## Getting Started

1. Install prerequisites:
   ```bash
   ./scripts/1-prerequisites/0-install-pipx.sh
   ./scripts/1-prerequisites/1-install-poetry.sh
   ```

2. Start observability stack:
   ```bash
   docker compose -f docker-compose.dev.yml up -d prometheus grafana
   ```

3. Access dashboards:
   - Grafana: http://localhost:3001 (admin/admin)
   - Prometheus: http://localhost:9090
