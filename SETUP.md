# Setup Guide

## Prerequisites

- Docker and Docker Compose installed
- API keys for at least one LLM provider

## Step-by-Step Setup

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd Multi-Source-Chatbot
```

### 2. Create Environment File

Create a `.env` file in the root directory:

```bash
# Required: At least one LLM API key
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here  # Optional
GOOGLE_API_KEY=your-google-api-key-here  # Optional

# Default settings
DEFAULT_LLM_PROVIDER=OPENAI
DEFAULT_MODEL=gpt-4o-mini
```

### 3. Build and Start Services

```bash
docker-compose up -d --build
```

This will:
- Build the backend Docker image
- Build the frontend Docker image
- Start both services

### 4. Verify Services

Check if services are running:

```bash
docker-compose ps
```

Check backend health:

```bash
curl http://localhost:8000/api/health
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

## Troubleshooting

### Port Already in Use

If ports 8000 or 3000 are already in use, modify `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Change host port
```

### API Key Issues

Ensure your API keys are correctly set in the `.env` file and that they're valid.

### Vector Database Issues

If you encounter vector database errors:

```bash
# Remove old data and restart
docker-compose down
rm -rf backend/data/vector_db
docker-compose up -d
```

### View Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

## Development Mode

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy .env.example to .env and configure
cp .env.example .env

# Run
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Production Deployment

1. Update environment variables for production
2. Configure CORS properly
3. Use HTTPS
4. Set up proper authentication
5. Use managed vector database for scaling

