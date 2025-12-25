"""
Research API endpoint for in-depth research automation.
"""

import time
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai

from gexa.config import settings
from gexa.database import get_async_db, ApiKey
from gexa.api.auth import get_api_key, increment_quota
from gexa.search import SearchService


router = APIRouter()


# Request/Response models
class ResearchRequest(BaseModel):
    """Request for research endpoint."""
    
    topic: str = Field(..., min_length=1, max_length=2000, description="Research topic or question")
    instructions: Optional[str] = Field(
        default=None, 
        description="Additional instructions for the research"
    )
    num_sources: int = Field(
        default=10, ge=3, le=50, description="Number of sources to gather"
    )
    depth: str = Field(
        default="standard", 
        description="Research depth: 'quick', 'standard', or 'deep'"
    )
    output_format: str = Field(
        default="report",
        description="Output format: 'report', 'bullets', or 'structured'"
    )


class ResearchSource(BaseModel):
    """Source used in research."""
    
    url: str
    title: Optional[str] = None
    relevance_score: float
    key_points: List[str] = []


class ResearchSection(BaseModel):
    """Section of a research report."""
    
    heading: str
    content: str
    sources: List[int] = []  # Indices into sources list


class ResearchResponse(BaseModel):
    """Response from research endpoint."""
    
    topic: str
    summary: str
    sections: List[ResearchSection] = []
    sources: List[ResearchSource] = []
    methodology: str
    took_ms: int


@router.post("", response_model=ResearchResponse)
async def conduct_research(
    request: ResearchRequest,
    api_key: ApiKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_async_db),
):
    """Conduct in-depth research on a topic.
    
    This endpoint performs multi-step research:
    1. Generates search queries from the topic
    2. Searches for relevant sources
    3. Extracts key information from sources
    4. Synthesizes findings into a structured report
    
    The 'depth' parameter controls how thorough the research is:
    - 'quick': 3-5 sources, brief summary
    - 'standard': 8-12 sources, detailed report
    - 'deep': 15-25 sources, comprehensive analysis
    """
    start_time = time.time()
    
    try:
        service = SearchService(db)
        
        # Adjust source count based on depth
        num_sources = request.num_sources
        if request.depth == "quick":
            num_sources = min(num_sources, 5)
        elif request.depth == "deep":
            num_sources = max(num_sources, 15)
        
        # Step 1: Generate search queries from topic
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.llm_model)
        
        query_prompt = f"""Generate 3-5 diverse search queries to research this topic thoroughly:

Topic: {request.topic}
{f'Additional instructions: {request.instructions}' if request.instructions else ''}

Output only the search queries, one per line. Make them specific and varied to cover different aspects."""

        query_response = model.generate_content(query_prompt)
        search_queries = [q.strip() for q in query_response.text.strip().split('\n') if q.strip()][:5]
        
        # Step 2: Search for sources using each query
        all_results = []
        seen_urls = set()
        
        for query in search_queries:
            try:
                search_result = await service.search(
                    query=query,
                    num_results=num_sources // len(search_queries) + 2,
                    include_content=True,
                    include_highlights=True,
                )
                
                for result in search_result["results"]:
                    if result["url"] not in seen_urls:
                        seen_urls.add(result["url"])
                        all_results.append(result)
            except Exception:
                continue
        
        # Limit to requested number
        all_results = all_results[:num_sources]
        
        # Step 3: Extract key points from each source
        sources = []
        source_contexts = []
        
        for i, result in enumerate(all_results):
            content = result.get("content", "")[:3000]
            highlights = result.get("highlights", [])
            
            # Extract key points
            if content:
                key_points_prompt = f"""Extract 2-3 key facts or insights from this content relevant to "{request.topic}":

{content[:2000]}

Output only bullet points, one per line starting with "-"."""

                try:
                    kp_response = model.generate_content(key_points_prompt)
                    key_points = [
                        p.strip().lstrip("- ").lstrip("• ")
                        for p in kp_response.text.strip().split('\n')
                        if p.strip() and (p.strip().startswith("-") or p.strip().startswith("•") or len(p.strip()) > 10)
                    ][:3]
                except Exception:
                    key_points = highlights[:3] if highlights else []
            else:
                key_points = highlights[:3] if highlights else []
            
            sources.append(ResearchSource(
                url=result["url"],
                title=result.get("title"),
                relevance_score=result.get("score", 0.5),
                key_points=key_points,
            ))
            
            source_contexts.append(f"[Source {i+1}] {result.get('title', 'Unknown')}\n{content[:1500]}")
        
        # Step 4: Synthesize research report
        combined_context = "\n\n".join(source_contexts[:12])  # Limit context size
        
        if request.output_format == "bullets":
            synthesis_prompt = f"""Based on these sources, create a bullet-point summary about: {request.topic}
{f'Instructions: {request.instructions}' if request.instructions else ''}

Sources:
{combined_context}

Create a comprehensive bullet-point summary with key findings. Reference sources by number (e.g., [1], [2]).
Format:
- Main finding or insight [source numbers]
- Another finding [source numbers]
..."""

        elif request.output_format == "structured":
            synthesis_prompt = f"""Based on these sources, create a structured analysis about: {request.topic}
{f'Instructions: {request.instructions}' if request.instructions else ''}

Sources:
{combined_context}

Create a structured analysis with these sections:
1. Overview (2-3 sentences)
2. Key Findings (3-5 bullet points with source references)
3. Details (organized by subtopic)
4. Conclusion (2-3 sentences)

Reference sources by number [1], [2], etc."""

        else:  # report format
            synthesis_prompt = f"""Based on these sources, write a comprehensive research report about: {request.topic}
{f'Instructions: {request.instructions}' if request.instructions else ''}

Sources:
{combined_context}

Write a well-structured report with:
- An executive summary (2-3 sentences)
- Main body organized by themes/subtopics
- Key insights and takeaways
- Reference sources by number [1], [2], etc.

Keep it informative and well-organized."""

        synthesis_response = model.generate_content(synthesis_prompt)
        report_text = synthesis_response.text
        
        # Parse into sections (simple parsing)
        sections = []
        current_section = None
        current_content = []
        
        for line in report_text.split('\n'):
            # Check if this is a heading
            if line.strip().startswith('#') or (line.strip() and line.strip().isupper() and len(line.strip()) < 100):
                if current_section:
                    sections.append(ResearchSection(
                        heading=current_section,
                        content='\n'.join(current_content).strip(),
                    ))
                current_section = line.strip().lstrip('#').strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Add last section
        if current_section:
            sections.append(ResearchSection(
                heading=current_section,
                content='\n'.join(current_content).strip(),
            ))
        elif current_content:
            sections.append(ResearchSection(
                heading="Research Findings",
                content='\n'.join(current_content).strip(),
            ))
        
        # Generate summary
        summary_prompt = f"""Summarize this research in 2-3 sentences:

{report_text[:2000]}"""

        summary_response = model.generate_content(summary_prompt)
        summary = summary_response.text.strip()
        
        # Increment quota
        await increment_quota(api_key, db, amount=num_sources + 3)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return ResearchResponse(
            topic=request.topic,
            summary=summary,
            sections=sections,
            sources=sources,
            methodology=f"Researched using {len(search_queries)} search queries across {len(sources)} sources. Depth: {request.depth}.",
            took_ms=elapsed_ms,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
