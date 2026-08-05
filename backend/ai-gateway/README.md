# AI Gateway Service

## Overview

The AI Gateway Service is the backend component of the AEV Platform. It provides a FastAPI-based service that acts as the entry point for AI requests.

---

## Features

- FastAPI application
- Health check endpoint
- Configuration management
- Ready for AI model integration
- API documentation with Swagger UI

---

## Project Structure

```
ai-gateway/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   └── main.py
│
├── README.md
└── requirements.txt
```

---

## Installation

Clone the repository:

```bash
git clone <repository-url>
```

Move into the project:

```bash
cd backend/ai-gateway
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Run the Application

```bash
uvicorn app.main:app --reload
```

Server:

```
http://127.0.0.1:8000
```

Swagger Documentation:

```
http://127.0.0.1:8000/docs
```

---

## API Endpoints

### Root

```
GET /
```

Response:

```json
{
  "message": "Welcome to AI Gateway Service"
}
```

---

### Health Check

```
GET /health
```

Response:

```json
{
  "status": "healthy",
  "service": "AI Gateway Service"
}
```

---

## Technology Stack

- Python
- FastAPI
- Uvicorn
- Pydantic

---

## Version

Current Version:

```
1.0.0
```