FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for PostgreSQL client and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini .

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Running migrations..."\n\
alembic upgrade head\n\
echo "Starting application..."\n\
exec uvicorn src.main:app --host 0.0.0.0 --port 8000\n' > /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]