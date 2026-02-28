# =========================
# Stage 1: Builder
# =========================
# FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime AS builder
FROM python:3.12.12-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Create and define the working directory
WORKDIR /app
COPY fastapi_app/requirements.txt .

# Install FastAPI dependencies and other necessary packages
# Install build dependencies, then remove them to keep the image size small
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential gcc && \
#     pip install --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt && \
#     apt-get remove -y build-essential gcc && \
#     apt-get autoremove -y && \
#     apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y build-essential gcc \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Stage 2: Final minimal image (no root)
# =========================
# FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime
FROM python:3.12.12-slim


ENV DEBIAN_FRONTEND=noninteractive

# Create a non-root user
# This user will run the application
RUN useradd --create-home --uid 1000 appuser

# Create and define the working directory
# Change ownership to the non-root user
# Copy the installed dependencies and application code from the builder stage
WORKDIR /app

# Copy dependencies and code
COPY --from=builder /usr/local /usr/local
COPY --chown=appuser:appuser Roberta_sentiment_model/ ./Roberta_sentiment_model
COPY --chown=appuser:appuser fastapi_app/ ./fastapi_app
COPY --chown=appuser:appuser src/ ./src

# Change to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 8000

CMD ["uvicorn", "fastapi_app.inference_api:app", "--host", "0.0.0.0", "--port", "8000"]
