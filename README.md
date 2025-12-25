# GEXA - Web Search API for AI Agents

A powerful web search API built for AI agents, similar to Exa.ai. Features semantic search, web crawling, content extraction, and AI-powered answers.

## Features

- 🔍 **Semantic Search** - Meaning-based search powered by embeddings
- 🕷️ **Web Crawling** - Playwright-based crawler with JavaScript rendering
- 📄 **Content Extraction** - Clean text extraction with Trafilatura
- 🤖 **AI Answers** - Generate answers with citations using Gemini
- 🔗 **Similar Pages** - Find semantically similar web pages
- 🚀 **Production Ready** - Rate limiting, API keys, and usage tracking

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL with pgvector extension
- Redis (optional, for task queue)

### Installation

```bash
# Clone and enter the project
cd GEXA

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium
```

### Database Setup

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE gexa;

-- Connect to gexa database
\c gexa

-- Enable pgvector extension
CREATE EXTENSION vector;
```

### Run the Server

```bash
# Apply migrations
alembic upgrade head

# Start the API server
uvicorn src.gexa.main:app --reload
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | POST | Semantic web search |
| `/contents` | POST | Get content from URLs |
| `/crawl` | POST | Crawl a website |
| `/findsimilar` | POST | Find similar pages |
| `/answer` | POST | AI-generated answer with citations |

## Example Usage

```python
from gexa_py import Gexa

gexa = Gexa("your-api-key")

# Search the web
results = gexa.search("latest AI research papers", num_results=10)

# Get content from a URL
content = gexa.get_contents(["https://example.com"])

# Find similar pages
similar = gexa.find_similar("https://openai.com")

# Get AI answer
answer = gexa.answer("What is transformer architecture?")
```

## License

MIT
