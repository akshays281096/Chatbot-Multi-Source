# Multi-Source Chatbot

A production-ready chatbot system that ingests data from multiple sources (documents, web pages, JSON) and answers user queries using RAG (Retrieval-Augmented Generation) with support for multiple LLM providers (OpenAI, Anthropic, Gemini).

The application features a modern, responsive frontend built with Next.js and Tailwind CSS, and a robust backend powered by FastAPI and LangChain.

## Features

### 🚀 Core Capabilities
- **Multi-Source Ingestion**
  - Upload documents (PDF, TXT, MD, DOCX)
  - Ingest web pages via URLs
  - Process structured JSON data


- **Advanced RAG Pipeline**
  - Vector database (ChromaDB) for efficient document storage
  - Semantic search across ingested documents
  - Automatic chunking and embedding
  - **Source Citations:** Responses include direct references to the source documents.

- **Multi-LLM Support**
  - **OpenAI** (GPT-4o, GPT-4, GPT-3.5)
  - **Anthropic** (Claude 3.5, Claude 3)
  - **Google Gemini** (Gemini 2.0, Gemini Pro)
  - Seamless model switching via the UI.

- **LangGraph Integration**
  - Tool-based workflow orchestration
  - Web scraping tool
  - RAG search tool
  - Dynamic tool selection based on query complexity.

### 🎨 Modern UI/UX
- **Responsive Design:** Fully responsive layout that works seamlessly on desktop, tablet, and mobile devices.
- **Collapsible Sidebar:** Space-saving sidebar for document management and settings, toggleable on smaller screens.
- **Dark Mode:** Native dark mode support for comfortable viewing in low-light environments.
- **Interactive Elements:**
  - Custom-styled dropdowns for model and document selection.
  - Real-time upload progress tracking.
  - Visual feedback for active states and loading indicators.
  - **Robot Avatar:** Distinctive AI avatar for assistant messages.

## Architecture

```mermaid
graph TD
    User[User] --> Frontend[Frontend (Next.js)]
    Frontend -->|HTTP/REST| Backend[Backend (FastAPI)]
    Backend -->|Orchestration| LangGraph[LangGraph Workflow]
    LangGraph -->|Retrieve| VectorDB[(ChromaDB)]
    LangGraph -->|Generate| LLM[LLM Provider]
    LLM --> OpenAI[OpenAI]
    LLM --> Anthropic[Anthropic]
    LLM --> Gemini[Google Gemini]
```

## Tech Stack

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **HTTP Client:** Axios
- **Rendering:** React Markdown

### Backend
- **Framework:** FastAPI
- **Language:** Python 3.10+
- **AI Orchestration:** LangChain, LangGraph
- **Vector Store:** ChromaDB
- **Data Processing:** Pandas, PyPDF2, BeautifulSoup4

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.10+ (for local backend development)
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

### 3. Start with Docker

```bash
docker-compose up --build
```


### 4. Stop the Docker

```bash
docker-compose down
```

This will start:
- **Backend API:** `http://localhost:8000`
- **Frontend:** `http://localhost:3000`

### 4. Access the Application

Open your browser and navigate to [http://localhost:3000](http://localhost:3000).

## API Endpoints

The backend provides comprehensive API documentation at `http://localhost:8000/docs`.

### Key Endpoints:
- `GET /api/health`: Health check
- `POST /api/ingest/document`: Upload and ingest files
- `POST /api/ingest/web`: Ingest web pages
- `POST /api/query`: Send queries to the chatbot

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Run the development server
npm run dev
```

## Project Structure

```
Multi-Source-Chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── routers/             # API endpoints
│   │   └── services/            # Business logic (RAG, LLM, Ingestion)
│   ├── data/                    # Data storage (Vector DB, Uploads)
│   └── requirements.txt
├── frontend/
│   ├── app/                     # Next.js pages and layout
│   ├── components/              # React components (ChatInterface, Sidebar, etc.)
│   ├── public/                  # Static assets
│   └── package.json
├── docker-compose.yml
└── README.md
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `DEFAULT_LLM_PROVIDER` | Default LLM provider | `OPENAI` |
| `DEFAULT_MODEL` | Default model name | `gpt-4o-mini` |
| `VECTOR_DB_PATH` | Path to vector database | `./data/vector_db` |

## License

[MIT License](LICENSE)
