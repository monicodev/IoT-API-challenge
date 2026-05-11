FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for PostgreSQL client and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .
RUN pip install --no-cache-dir "alembic[async]" asyncpg

# Copy application code
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini .

# Create startup script that uses environment variables
RUN echo '#!/bin/bash\n\
set -e\n\
# Configure alembic with environment variables\n\
export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"\n\
alembic upgrade head\n\
exec uvicorn src.main:app --host 0.0.0.0 --port 8000\n' > /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]