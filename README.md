# Multi-Source Chatbot

A production-ready chatbot system that ingests data from multiple sources (documents, web pages, JSON) and answers user queries using RAG (Retrieval-Augmented Generation) with support for multiple LLM providers (OpenAI, Anthropic, Gemini).

## Features

- **Multi-Source Ingestion**
  - Upload documents (PDF, TXT, MD, DOCX)
  - Ingest web pages via URLs
  - Process structured JSON data
  - OCR support for images and scanned PDFs

- **RAG Pipeline**
  - Vector database (ChromaDB) for document storage
  - Semantic search across ingested documents
  - Automatic chunking and embedding
  - Source references in responses

- **Multi-LLM Support**
  - OpenAI (GPT-4o, GPT-4, GPT-3.5)
  - Anthropic (Claude 3.5, Claude 3)
  - Google Gemini (Gemini 2.0, Gemini Pro)
  - Easy model switching via API

- **LangGraph Integration**
  - Tool-based workflow orchestration
  - Web scraping tool
  - RAG search tool
  - Dynamic tool selection

- **Production Ready**
  - Docker containerization
  - Environment-based configuration
  - Persistent data storage
  - Comprehensive logging
  - Health check endpoints

## Architecture

```
┌─────────────┐
│   Frontend  │ (Next.js)
│  (Next.js)  │
└──────┬──────┘
       │
       │ HTTP/REST
       │
┌──────▼──────┐
│   Backend   │ (FastAPI)
│  (Python)   │
└──────┬──────┘
       │
       ├──► LangGraph ──► LLM (OpenAI/Anthropic/Gemini)
       │
       ├──► Vector Store (ChromaDB)
       │
       └──► Tools (Web Scraper, RAG Search)
```

## Prerequisites

- Docker and Docker Compose
- API keys for at least one LLM provider:
  - OpenAI API key
  - Anthropic API key (optional)
  - Google API key (optional)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Multi-Source-Chatbot
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```bash
# LLM API Keys (at least one required)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Optional
GOOGLE_API_KEY=your_google_api_key_here  # Optional

# Default LLM Provider
DEFAULT_LLM_PROVIDER=OPENAI
DEFAULT_MODEL=gpt-4o-mini
```

### 3. Start the Services

```bash
docker-compose up -d
```

This will start:
- Backend API on `http://localhost:8000`
- Frontend on `http://localhost:3000`

### 4. Access the Application

Open your browser and navigate to:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

## API Endpoints

### Health Check

```bash
GET /api/health
```

### Document Ingestion

```bash
POST /api/ingest/document
Content-Type: multipart/form-data

file: <file>
source_name: <optional>
```

Supported file types: PDF, TXT, MD, DOCX

### Web Page Ingestion

```bash
POST /api/ingest/web
Content-Type: multipart/form-data

url: <url>
```

### JSON Ingestion

```bash
POST /api/ingest/json
Content-Type: multipart/form-data

file: <json_file>
source_name: <optional>
```

### Query Endpoint

```bash
POST /api/query
Content-Type: application/json

{
  "query": "What is the main topic of the uploaded documents?",
  "llm_provider": "OPENAI",  # Optional: OPENAI, ANTHROPIC, GEMINI
  "model": "gpt-4o-mini",    # Optional
  "conversation_history": []  # Optional
}
```

Response:
```json
{
  "response": "The main topic is...",
  "references": [
    "pdf: document1.pdf",
    "web_page: https://example.com"
  ],
  "status": "success"
}
```

## Usage Examples

### Using cURL

#### 1. Upload a Document

```bash
curl -X POST http://localhost:8000/api/ingest/document \
  -F "file=@document.pdf" \
  -F "source_name=My Document"
```

#### 2. Ingest a Web Page

```bash
curl -X POST http://localhost:8000/api/ingest/web \
  -F "url=https://example.com/article"
```

#### 3. Query the Chatbot

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key points in the uploaded documents?",
    "llm_provider": "OPENAI",
    "model": "gpt-4o-mini"
  }'
```

### Using Python

```python
import requests

# Upload document
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/ingest/document',
        files={'file': f},
        data={'source_name': 'My Document'}
    )
print(response.json())

# Query
response = requests.post(
    'http://localhost:8000/api/query',
    json={
        'query': 'What is this document about?',
        'llm_provider': 'OPENAI',
        'model': 'gpt-4o-mini'
    }
)
print(response.json())
```

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=your_key
export ANTHROPIC_API_KEY=your_key
export GOOGLE_API_KEY=your_key

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
Multi-Source-Chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py             # Configuration settings
│   │   ├── routers/              # API routes
│   │   │   ├── health.py
│   │   │   ├── ingestion.py
│   │   │   └── query.py
│   │   └── services/             # Business logic
│   │       ├── langgraph_service.py
│   │       ├── vector_store.py
│   │       ├── llm_factory.py
│   │       ├── document_processor.py
│   │       ├── web_scraper.py
│   │       └── ocr.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/                      # Next.js app directory
│   ├── components/               # React components
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `GOOGLE_API_KEY` | Google API key | Optional |
| `DEFAULT_LLM_PROVIDER` | Default LLM provider | `OPENAI` |
| `DEFAULT_MODEL` | Default model name | `gpt-4o-mini` |
| `VECTOR_DB_PATH` | Path to vector database | `./data/vector_db` |
| `UPLOAD_DIR` | Upload directory | `./data/uploads` |
| `LOG_FILE` | Log file path | `./logs/chatbot.log` |

## Data Persistence

Data is persisted in Docker volumes:
- `./backend/data/vector_db` - Vector database (ChromaDB)
- `./backend/data/uploads` - Uploaded files (temporary)
- `./backend/logs` - Application logs

## Logging

Logs are written to:
- Console (stdout)
- File: `./logs/chatbot.log` (JSON format)

Log levels: DEBUG, INFO, WARNING, ERROR

## Troubleshooting

### Backend won't start

1. Check API keys are set correctly
2. Verify ports 8000 is not in use
3. Check logs: `docker-compose logs backend`

### Vector database errors

1. Ensure `./backend/data` directory exists and is writable
2. Check disk space
3. Restart the backend service

### Frontend can't connect to backend

1. Verify backend is running: `curl http://localhost:8000/api/health`
2. Check `NEXT_PUBLIC_API_URL` environment variable
3. Ensure CORS is configured correctly

## Production Deployment

### Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **CORS**: Configure allowed origins in production
3. **Rate Limiting**: Add rate limiting middleware
4. **Authentication**: Add authentication/authorization
5. **HTTPS**: Use HTTPS in production

### Scaling

- Use a managed vector database (Pinecone, Weaviate) for production
- Add Redis for caching
- Use a load balancer for multiple backend instances
- Consider using a message queue for async processing

## License

[Your License Here]

## Contributing

[Contributing Guidelines]

## Support

For issues and questions, please open an issue on GitHub.
