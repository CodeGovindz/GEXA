<p align="center">
  <img src="https://img.shields.io/badge/GEXA-Web%20Search%20API-6366f1?style=for-the-badge&logo=searchengin&logoColor=white" alt="GEXA">
</p>

<h1 align="center">🔍 GEXA</h1>

<p align="center">
  <strong>Web Search API for AI Agents</strong><br>
  <em>Semantic search, web crawling, and AI-powered answers - built for the next generation of AI applications</em>
</p>

<p align="center">
  <a href="https://github.com/CodeGovindz/GEXA/actions"><img src="https://img.shields.io/badge/build-passing-brightgreen?style=flat-square" alt="Build Status"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI"></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-api-endpoints">API</a> •
  <a href="#-python-sdk">SDK</a> •
  <a href="#-dashboard">Dashboard</a> •
  <a href="#-docs">Docs</a>
</p>

---

## ✨ Features

<table>
  <tr>
    <td align="center" width="33%">
      <h3>🔍 Semantic Search</h3>
      <p>Meaning-based search powered by Google's text-embedding-004 model</p>
    </td>
    <td align="center" width="33%">
      <h3>🕷️ Web Crawling</h3>
      <p>Playwright-based crawler with full JavaScript rendering</p>
    </td>
    <td align="center" width="33%">
      <h3>📄 Content Extraction</h3>
      <p>Clean text & markdown extraction with Trafilatura</p>
    </td>
  </tr>
  <tr>
    <td align="center" width="33%">
      <h3>🤖 AI Answers</h3>
      <p>Generate answers with citations using Gemini 2.5 Flash</p>
    </td>
    <td align="center" width="33%">
      <h3>📊 Deep Research</h3>
      <p>Multi-source research reports with key points synthesis</p>
    </td>
    <td align="center" width="33%">
      <h3>🔗 Similar Pages</h3>
      <p>Find semantically similar web pages using vector similarity</p>
    </td>
  </tr>
</table>

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| PostgreSQL | 14+ with pgvector |
| Redis | 6+ (optional) |

### Installation

```bash
# Clone the repository
git clone https://github.com/CodeGovindz/GEXA.git
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
-- Create database and enable pgvector
CREATE DATABASE gexa;
\c gexa
CREATE EXTENSION vector;
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Required: GEMINI_API_KEY, DATABASE_URL
```

### Run the Server

```bash
# Apply database migrations
alembic upgrade head

# Start the API server
$env:PYTHONPATH="src"  # Windows PowerShell
uvicorn gexa.main:app --host 127.0.0.1 --port 8000
```

> ⚠️ **Windows Note:** Don't use `--reload` flag due to Playwright subprocess compatibility

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|:---------|:------:|:------------|
| `/search` | `POST` | 🔍 Semantic web search with embeddings |
| `/contents` | `POST` | 📄 Crawl & extract content from URLs |
| `/crawl` | `POST` | 🕷️ Background site crawling |
| `/findsimilar` | `POST` | 🔗 Find semantically similar pages |
| `/answer` | `POST` | 🤖 AI answers with citations |
| `/research` | `POST` | 📊 In-depth research reports |
| `/keys` | `GET/POST/DELETE` | 🔑 API key management |

### API Documentation

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Dashboard:** http://localhost:8000/dashboard/

---

## 🐍 Python SDK

Install the SDK:

```bash
pip install gexa-py  # Coming soon to PyPI
# Or install from source:
pip install -e sdk/python
```

### Usage

```python
from gexa_py import Gexa

# Initialize client
gexa = Gexa("your-api-key", base_url="http://localhost:8000")

# 🔍 Semantic Search
results = gexa.search("latest AI research papers", num_results=10)

# 📄 Get Content from URLs
content = gexa.get_contents(["https://example.com"])

# 🔗 Find Similar Pages
similar = gexa.find_similar("https://openai.com")

# 🤖 Get AI Answer
answer = gexa.answer("What is transformer architecture?")

# 📊 Deep Research
research = gexa.research(
    topic="Benefits of machine learning in healthcare",
    depth="deep"
)
```

### Async Support

```python
from gexa_py import AsyncGexa

async def main():
    async with AsyncGexa("your-api-key") as gexa:
        results = await gexa.search("async search query")
        print(results)
```

---

## 🎨 Dashboard

GEXA includes a modern web dashboard for testing and API key management.

<p align="center">
  <strong>Access at:</strong> <code>http://localhost:8000/dashboard/</code>
</p>

### Features
- 🧪 **Playground** - Test all API endpoints interactively
- 🔑 **API Keys** - Create, copy, and delete API keys
- 📊 **Usage** - Monitor API usage (coming soon)
- 📚 **Docs** - Quick reference and links

---

## 🛠️ Tech Stack

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" alt="Playwright">
  <img src="https://img.shields.io/badge/Google_Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini">
</p>

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI |
| **Database** | PostgreSQL + pgvector |
| **LLM** | Google Gemini 2.5 Flash |
| **Embeddings** | Google text-embedding-004 |
| **Crawler** | Playwright (Chromium) |
| **Content Extraction** | Trafilatura |

---

## 📁 Project Structure

```
GEXA/
├── src/gexa/           # Core API source code
│   ├── api/            # FastAPI routes
│   ├── crawler/        # Web crawling engine
│   ├── search/         # Vector search & embeddings
│   └── database/       # Models & schemas
├── sdk/python/         # Python SDK
├── dashboard/          # Web dashboard UI
├── alembic/            # Database migrations
└── tests/              # Test suite
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/CodeGovindz">CodeGovindz</a>
</p>

<p align="center">
  <a href="https://github.com/CodeGovindz/GEXA">⭐ Star this repo</a> •
  <a href="https://github.com/CodeGovindz/GEXA/issues">🐛 Report Bug</a> •
  <a href="https://github.com/CodeGovindz/GEXA/issues">💡 Request Feature</a>
</p>
