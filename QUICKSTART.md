# Quick Start Guide

Get the Multi-Source Chatbot running in 5 minutes!

## Prerequisites

- Docker and Docker Compose
- OpenAI API key (or Anthropic/Google API key)

## Steps

### 1. Setup Environment

```bash
# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
DEFAULT_LLM_PROVIDER=OPENAI
DEFAULT_MODEL=gpt-4o-mini
EOF
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Verify

```bash
# Check health
curl http://localhost:8000/api/health

# Open in browser
open http://localhost:3000
```

## First Steps

1. **Upload a Document**
   - Click "Document" tab
   - Upload a PDF, TXT, or MD file

2. **Or Ingest a Web Page**
   - Click "Web Page" tab
   - Enter a URL (e.g., https://example.com)
   - Click "Ingest"

3. **Ask a Question**
   - Type your question in the chat
   - Get an answer with source references!

## Example API Calls

### Upload Document
```bash
curl -X POST http://localhost:8000/api/ingest/document \
  -F "file=@document.pdf"
```

### Query
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}'
```

## Troubleshooting

**Services won't start?**
```bash
docker-compose logs
```

**Port conflict?**
Edit `docker-compose.yml` and change ports.

**API key error?**
Check your `.env` file has the correct API key.

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [SETUP.md](SETUP.md) for detailed setup instructions

