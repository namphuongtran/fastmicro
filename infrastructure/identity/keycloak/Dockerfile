ARG SDK_IMAGE=quay.io/keycloak/keycloak:26.3.1

# Use the official Keycloak image as the base
FROM ${SDK_IMAGE} as builder

# Enable health and metrics support
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true
ENV KC_DB=postgres

WORKDIR /opt/keycloak

# Run the build command to set server build options to create an optimized image
RUN /opt/keycloak/bin/kc.sh build \
    --db=${KC_DB} \
    --health-enabled=${KC_HEALTH_ENABLED} \
    --metrics-enabled=${KC_METRICS_ENABLED}

# Start a new build stage to create a slimmed-down final image
FROM ${SDK_IMAGE}

# Copy the optimized Keycloak from the builder stage
COPY --from=builder /opt/keycloak/ /opt/keycloak/

# Set the entrypoint to the Keycloak start command
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]