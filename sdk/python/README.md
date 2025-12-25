# GEXA Python SDK

Official Python SDK for [GEXA](https://github.com/CodeGovindz/GEXA) - Web Search API for AI Agents.

## Installation

```bash
pip install gexa-py
```

Or install from source:

```bash
cd sdk/python
pip install -e .
```

## Quick Start

```python
from gexa_py import Gexa

# Initialize with your API key
gexa = Gexa("your-api-key", base_url="http://localhost:8000")

# Search the web
results = gexa.search("latest AI research papers", num_results=10)
for result in results.results:
    print(f"{result.title}: {result.url}")

# Get content from URLs
contents = gexa.get_contents(["https://example.com"])
print(contents.results[0].content)

# Find similar pages
similar = gexa.find_similar("https://openai.com")

# Get AI-powered answer
answer = gexa.answer("What is transformer architecture?")
print(answer.answer)
```

## Async Support

```python
import asyncio
from gexa_py import AsyncGexa

async def main():
    async with AsyncGexa("your-api-key") as gexa:
        results = await gexa.search("AI papers")
        print(results)

asyncio.run(main())
```

## API Reference

### `Gexa(api_key, base_url)`

Initialize the GEXA client.

- `api_key`: Your GEXA API key
- `base_url`: API server URL (default: `http://localhost:8000`)

### Methods

| Method | Description |
|--------|-------------|
| `search(query, ...)` | Semantic web search |
| `get_contents(urls, ...)` | Extract content from URLs |
| `find_similar(url, ...)` | Find similar pages |
| `answer(query, ...)` | Get AI-powered answer |
| `crawl(url, ...)` | Start a crawl job |
| `get_crawl_status(job_id)` | Check crawl status |

## License

MIT
