FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY app ./app

# --frozen: use the exact versions in uv.lock (the ones the test suite ran
# against), fail the build instead of silently re-resolving if it's stale.
RUN uv sync --no-dev --frozen

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
