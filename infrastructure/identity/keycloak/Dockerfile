ARG SDK_IMAGE=quay.io/keycloak/keycloak:26.3.1


# Use the official Keycloak image as the base
FROM ${SDK_IMAGE} as builder

ARG TRANSACTION_XA_ENABLED=false
ARG DB=postgres
ARG HTTP_RELATIVE_PATH=/
# Install curl to download custom providers
# RUN apt update \
#   && apt install -y curl \
#   && apt-get clean \
#   && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Enable health and metrics support
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true
ENV KC_HTTP_ENABLED=true
ENV KC_HTTP_RELATIVE_PATH=${HTTP_RELATIVE_PATH}
# Configure the database vendor to MSSQL
ENV KC_DB=${DB}

# Install custom providers
# RUN curl -sL https://github.com/aerogear/keycloak-metrics-spi/releases/download/2.5.3/keycloak-metrics-spi-2.5.3.jar -o /opt/keycloak/providers/keycloak-metrics-spi-2.5.3.jar

# RUN /opt/keycloak/bin/kc.sh build

WORKDIR /opt/keycloak
# for demonstration purposes only, please make sure to use proper certificates in production instead
#RUN keytool -genkeypair -storepass password -storetype PKCS12 -keyalg RSA -keysize 2048 -dname "CN=server" -alias server -ext "SAN:c=DNS:localhost,IP:127.0.0.1" -keystore conf/server.keystore
#RUN /opt/keycloak/bin/kc.sh --verbose  build 
#RUN /opt/keycloak/bin/kc.sh -Dkc.db.tx-type=enable -Dkc.db-driver=com.microsoft.sqlserver.jdbc.SQLServerDriver --db=mssql

# Run the build command to set server build options to create an optimized image
RUN /opt/keycloak/bin/kc.sh build --db=${DB} --transaction-xa-enabled=${TRANSACTION_XA_ENABLED} --http-relative-path=${KC_HTTP_RELATIVE_PATH} --health-enabled=${KC_HEALTH_ENABLED} --metrics-enabled=${KC_METRICS_ENABLED}

# Copy the custom configurations if any
# COPY your_custom_configurations /opt/keycloak/conf/

# Start a new build stage to create a slimmed-down final image
FROM ${SDK_IMAGE}

# Copy the optimized Keycloak from the builder stage
COPY --from=builder /opt/keycloak/ /opt/keycloak/

# Configure the database vendor
ENV KC_DB=${DB}
ENV KC_HTTP_RELATIVE_PATH=${HTTP_RELATIVE_PATH}

# Set the entrypoint to the Keycloak start command
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]

# Start Keycloak in the dev mode (use 'start' for production mode)
CMD ["start"]