#!/usr/bin/env bash
docker compose up -d --build keycloak
docker compose up -d --build federation-gateway
docker compose up -d --build cert-generator
docker compose up -d --build traefik