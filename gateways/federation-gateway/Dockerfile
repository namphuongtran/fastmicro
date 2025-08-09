FROM python:3.12-slim

# ENV PYTHONUNBUFFERED=1 \
#     POETRY_VERSION=2.1.0 \
#     POETRY_HOME="/opt/poetry" \
#     PATH="/opt/poetry/bin:$PATH"

# # Install system dependencies
# RUN apt-get update && apt-get install -y curl build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# # Install Poetry
# RUN curl -sSL https://install.python-poetry.org | python3 - && chmod -R 755 /opt/poetry

# WORKDIR /app

# # Copy source code first (before poetry install so deps are found)
# COPY libs/settings/pyproject.toml ./libs/settings/pyproject.toml
# COPY libs/settings/src ./libs/settings/src

# COPY gateways/federation-gateway/pyproject.toml gateways/federation-gateway/poetry.lock* ./

# # Install dependencies
# RUN poetry config virtualenvs.create false && poetry install --no-root

# # Copy app source
# COPY gateways/federation-gateway/src ./src

# Install Poetry
RUN pip install poetry
RUN poetry config virtualenvs.create false

# Recreate the directory structure to match the relative paths in pyproject.toml
WORKDIR /app/gateways/federation-gateway

# Copy libs to maintain the correct relative path structure
COPY libs/ /app/libs/

# Copy user-service files
COPY gateways/federation-gateway/pyproject.toml ./
COPY gateways/federation-gateway/poetry.lock ./

# Install dependencies (now the relative path ../../libs/settings will work)
RUN poetry install --only=main,local

# Copy source code
COPY gateways/federation-gateway/src/ ./src/

# Set Python path
ENV PYTHONPATH=/app/gateways/federation-gateway/src:$PYTHONPATH

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

EXPOSE 44381

CMD ["poetry", "run", "uvicorn", "src.federation_gateway.main:app", "--host", "0.0.0.0", "--port", "44381"]
