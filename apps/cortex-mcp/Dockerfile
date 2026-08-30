FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY cortex_mcp/ ./cortex_mcp/

RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
ENV PORT=3100

EXPOSE 3100

CMD ["python", "-m", "cortex_mcp.server"]
