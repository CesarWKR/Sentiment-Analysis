# =========================
# Stage 1: Build Stage
# =========================
# This stage installs all Python dependencies so they
# can be reused in the final image without re-installing
# them every time the code changes.
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime AS builder


# Set working directory
WORKDIR /app


# Copy only dependency definitions first (better cache usage)
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# =========================
# Stage 2: Final runtime image
# =========================

FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

# Disable interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive 

# -----------------------------------------------------
# Create a non-root user for security and DevContainer
# compatibility (VS Code Remote Containers)
# -----------------------------------------------------
# UID 1000 is commonly used by VS Code dev containers
RUN useradd --create-home --uid 1000 --shell /bin/bash appuser

# Create and define the working directory changing ownership to the non-root user
WORKDIR /app

# Ensure the working directory exists and belongs to the non-root user
RUN mkdir -p /app && chown -R appuser:appuser /app

# -----------------------------------------------------
# Copy Python dependencies from the builder stage
# -----------------------------------------------------
# This copies all installed Python packages and binaries
# into the final image without reinstalling them
COPY --from=builder /usr/local /usr/local

# -----------------------------------------------------
# Copy application source code
# -----------------------------------------------------
# Ownership is set to appuser to avoid permission issues
# when using VS Code Dev Containers
COPY --chown=appuser:appuser . .

# -----------------------------------------------------
# Switch to non-root user
# -----------------------------------------------------
USER appuser

# -----------------------------------------------------
# Default command
# -----------------------------------------------------
# Runs the full pipeline:
# - Reddit data extraction
# - Kafka producer & consumer
# - Data processing
# - Model training & export
CMD ["python", "main.py"]

# -----------------------------------------------------
# Alternative command for development/debugging
# (uncomment if needed)
# -----------------------------------------------------
# CMD ["sleep", "infinity"]