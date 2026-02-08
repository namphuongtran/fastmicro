# =============================================================================
# Keycloak Identity Provider - Custom Build
# =============================================================================
# Based on official Keycloak image with custom themes and configurations
# =============================================================================

FROM quay.io/keycloak/keycloak:24.0 AS builder

# Enable health and metrics support
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true

# Configure database vendor
ENV KC_DB=postgres

# Build optimized Keycloak
RUN /opt/keycloak/bin/kc.sh build

# Production stage
FROM quay.io/keycloak/keycloak:24.0

COPY --from=builder /opt/keycloak/ /opt/keycloak/

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
