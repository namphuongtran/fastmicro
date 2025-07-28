FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pipx and poetry
RUN python -m pip install --user pipx && \
    /root/.local/bin/pipx install poetry

# Copy requirements and install Python dependencies
COPY pyproject.toml .

# Install project dependencies using poetry
RUN poetry install --no-root -vvv

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 44381

CMD ["poetry", "run", "uvicorn", "src.federation_gateway.main:app", "--host", "0.0.0.0", "--port", "44381", "--reload"]