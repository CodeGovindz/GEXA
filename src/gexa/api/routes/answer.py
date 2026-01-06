"""
Answer API endpoint using Gemini for AI-generated answers.
Supports structured JSON output similar to Olostep.
"""

import json
import time
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai

from gexa.config import settings
from gexa.database import get_async_db, ApiKey
from gexa.database.schemas import AnswerRequest, AnswerResponse, Citation
from gexa.api.auth import get_api_key, increment_quota
from gexa.search import SearchService


router = APIRouter()


def generate_json_schema_prompt(json_format: Dict[str, Any]) -> str:
    """Generate a prompt that instructs Gemini to output in the given JSON schema."""
    schema_str = json.dumps(json_format, indent=2)
    return f"""
You MUST respond with a valid JSON object that matches this exact schema:
{schema_str}

Fill in the values based on the information gathered. If a value is unknown, use null.
Output ONLY the JSON object, no additional text or markdown formatting.
"""


def parse_json_response(text: str) -> Dict[str, Any]:
    """Parse JSON from Gemini response, handling common formatting issues."""
    # Remove markdown code blocks if present
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Return as error dict if parsing fails
        return {"error": "Failed to parse JSON response", "raw_response": text}


@router.post("", response_model=AnswerResponse)
async def answer_question(
    request: AnswerRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Get an AI-generated answer with citations.
    
    Searches the web for relevant information and generates
    a comprehensive answer using Gemini, with citations to
    the source pages.
    
    Features:
    - Query rewriting for disambiguation
    - Hybrid approach (web search + LLM knowledge)
    - Structured JSON output (json_format parameter)
    """
    start_time = time.time()
    
    try:
        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.llm_model)
        rewrite_model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        # Step 1: Rewrite the user's question into an optimized search query
        rewrite_prompt = f"""You are a search query optimizer. Convert the user's question into an optimal web search query.

CRITICAL DISAMBIGUATION RULES:
1. "capital" in geographic context → use "capital city" (e.g., "capital of France" → "Paris capital city France")
2. "capital" in financial context → keep as "capital" or use "capital investment/money"
3. Add the ACTUAL ANSWER if known (e.g., "capital of Japan" → "Tokyo capital city Japan population")
4. Replace pronouns with specific entities
5. Remove question words (what, how, why, when)
6. Add terms that clarify intent (geography, economy, history, etc.)

Examples:
- "What is the capital of Japan?" → "Tokyo Japan capital city"
- "What is the population of Tokyo?" → "Tokyo population 2024 demographics"
- "Who is the CEO of Apple?" → "Tim Cook Apple CEO"
- "How much capital does a startup need?" → "startup capital investment funding amount"

Question: {request.query}

Search query (output ONLY the optimized search query, nothing else):"""
        
        try:
            rewrite_response = rewrite_model.generate_content(rewrite_prompt)
            optimized_query = rewrite_response.text.strip().strip('"').strip("'")
            if not optimized_query or len(optimized_query) < 3:
                optimized_query = request.query
        except Exception:
            optimized_query = request.query
        
        # Step 2: Search with the optimized query
        service = SearchService(db)
        
        search_result = await service.search(
            query=optimized_query,
            num_results=request.num_sources,
            include_content=True,
            include_highlights=True,
        )
        
        # Step 3: Prepare context from search results
        context_parts = []
        citations = []
        
        for i, result in enumerate(search_result["results"]):
            if result.get("content"):
                content = result["content"][:3000]
                context_parts.append(f"[Source {i+1}]: {result.get('title', 'Unknown')}\n{content}")
                
                if request.include_citations:
                    snippet = result.get("highlights", [content[:200]])[0] if result.get("highlights") else content[:200]
                    citations.append(Citation(
                        url=result["url"],
                        title=result.get("title"),
                        snippet=snippet,
                    ))
        
        context = "\n\n".join(context_parts)
        
        # Step 4: Generate answer - handle both plain text and structured JSON
        structured_answer = None
        
        if request.json_format:
            # Structured JSON output mode (like Olostep)
            json_schema_instruction = generate_json_schema_prompt(request.json_format)
            
            prompt = f"""Answer this question: {request.query}

I have gathered the following web sources:
{context if context else "No relevant sources were found."}

Instructions:
1. Extract the requested information from the sources or use your knowledge if sources are insufficient
2. For factual questions, prioritize accuracy
{json_schema_instruction}"""
            
            response = model.generate_content(prompt)
            answer_text = response.text
            structured_answer = parse_json_response(answer_text)
            
            # Also generate a human-readable answer
            answer_text = f"Structured response generated. See structured_answer field for JSON data."
            
        else:
            # Regular text answer with hybrid approach
            prompt = f"""Answer this question: {request.query}

I have gathered the following web sources:
{context if context else "No relevant sources were found."}

Instructions:
1. First, try to answer using the sources above if they contain relevant information
2. If the sources DON'T contain the answer or are irrelevant to the question, use your own knowledge to provide an accurate answer
3. Be transparent: if you're using your own knowledge instead of sources, say "Based on my knowledge..." 
4. If using sources, cite them (e.g., "According to Source 1...")
5. Provide a comprehensive, well-structured answer
6. For factual questions (capitals, populations, dates, etc.), prioritize accuracy over source citation

Answer:"""
            
            response = model.generate_content(prompt)
            answer_text = response.text
        
        # Increment quota (search + answer generation)
        await increment_quota(api_key, db, amount=2)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return AnswerResponse(
            query=request.query,
            answer=answer_text,
            structured_answer=structured_answer,
            citations=citations if request.include_citations else [],
            took_ms=elapsed_ms,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
