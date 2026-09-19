# Base image with Python 3.12 (matches the AEV Platform's stack: Python 3.12, FastAPI)
FROM python:3.12-slim

# Set working directory inside the container
WORKDIR /code

# Install dependencies first (separate layer = faster rebuilds when only code changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# The port uvicorn will run on inside the container
EXPOSE 8000

# Start the server, listening on all interfaces so docker-compose/other
# containers can reach it (127.0.0.1 would only be reachable from inside
# this container)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
