# Use a stable, lightweight Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies if needed (e.g., for SQLite or network tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create the persistent data directory for SQLite and manifests
RUN mkdir -p /app/data && chmod 777 /app/data

# Expose Port 8000 for the FastAPI SaaS server
# Expose Port 8501 if you also want to run the Streamlit Dashboard
EXPOSE 8000
EXPOSE 8501

# Start the FastAPI server using uvicorn
# We use 0.0.0.0 so the server is reachable outside the container
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
