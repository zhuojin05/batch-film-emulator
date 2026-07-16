FROM python:3.11-slim

# Set environment variables to optimize Python runtime in Docker
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy dependency list and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/

# Create internal mount directories to mirror host volume configuration
RUN mkdir -p /luts /input /output

# Default command displays the CLI help screen
CMD ["python", "src/grade.py", "--help"]
