from typing import List, Literal, Optional, get_args
from pydantic import BaseModel, Field
import os
import instructor
import asyncio
import httpx
import time
import json
from .db import fetch_all_posts

# Level 1 Required Enum + Necessary Extensions
RelationshipType = Literal[
    "founder", "ceo", "employee", "investor", "competitor", 
    "parentCompany", "subsidiary", "partner", "acquiredBy", 
    "boardMember", "advisor", "alumniOf", "affiliation",
    "opponent", "productOf", "creatorOf", "other"
]

ALLOWED_RELATIONS = ", ".join(get_args(RelationshipType))


class Entity(BaseModel):
    raw_name: str = Field(..., description="Exact name used in text (e.g., 'Sama', 'The Zuck')")
    canonical_name: str = Field(..., description="Formalized entity name (e.g., 'Sam Altman', 'Mark Zuckerberg')")

class Triplet(BaseModel):
    subject: Entity
    relationship: RelationshipType
    object: Entity
    evidence: str = Field(..., description="The specific phrase in the post that justifies this relationship.")
    suggested_relationship_evidence: Optional[str] = Field(..., description="justification for new suggested relationship, if relationship is of the type 'other'.")
    suggested_relationship: Optional[str] = Field(..., description="A new relationship type suggested by the LLM, if any.")

class PostAnalysis(BaseModel):
    has_business_info: bool = Field(..., description="Set to False if the post is just opinions/rants without hard relationships.")
    justification: Optional[str] = Field(..., description="Briefly explain why this post contains (or lacks) valid business triplets.")
    triplets: List[Triplet] = Field(default_factory=list)
    post_id: str = Field(..., description="The unique identifier of the Reddit post analyzed.")
    post_url: str = Field(None, description="The URL of the Reddit post.")

class BatchExtraction(BaseModel):
    results: List[PostAnalysis]


SYSTEM_PROMPT = """
You are a Corporate Intelligence Specialist. Your task is to extract structured business and leadership relationships from Reddit posts.

### ALLOWED RELATIONSHIPS:
The ONLY permitted relationship types are: {ALLOWED_RELATIONS}

### EXTRACTION RULES:
1. **Focus on Structure**: 
   - Only extract known relationships. 
   - If there is a business or leadership relationship present in the post, but not available in the allowed list, specify relationship as 'other' and provide a new suggested relationship in 'suggested_relationship'.
   - If suggesting a new relationship, provide clear evidence from the post in 'suggested_relationship_evidence'. 
2. **Strict Filtering**: 
   - If a post is a personal anecdote, a product review, or an emotional rant (e.g., 'I love GPT-4o'), mark `has_business_info` as False and return an empty triplet list.
   - DO NOT extract 'User — uses — Product' or 'Person — hates — Company'.
3. **Canonicalization**: Normalize all entities. 
   - 'OpenAI's boss' -> Sam Altman.
   - 'The fruit company' -> Apple Inc.
   - 'ChatGPT' -> ChatGPT (Entity: OpenAI, Relationship: creatorOf, Object: ChatGPT).
4. **Relationship Inference**: 
   - 'X announced...' -> (X, ceo, Company)
   - 'X criticized OpenAI's strategy' -> (X, opponent, OpenAI)
   - 'X is trying to beat Y' -> (X, competitor, Y)
5. **Resolution**: Ensure that if the same entity appears across different posts in this batch, the 'canonical_name' remains perfectly consistent.

Return ONLY a valid JSON object matching the provided schema.
"""

def get_llm_triplets(posts: List[dict]) -> BatchExtraction:
    """
    Given a list of post dicts {'id': str, 'text': str, 'url': str}, 
    extracts business triplets using LLM.
    """
    if not posts:
        return BatchExtraction(results=[])

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("TRIPLET_EXTRACTOR_MODEL", "openrouter/google/gemini-2.0-flash-001")

    # Combine posts into a single formatted string for batch processing
    formatted_posts = format_posts_for_llm(posts)

    try:
        mode = instructor.Mode.OPENROUTER_STRUCTURED_OUTPUTS
        client = instructor.from_provider(model, api_key=api_key, mode=mode)
        
        # We pass the schema to response_model to ensure structured output
        start_llm = time.time()
        print(f"Sending batch of {len(posts)} posts to LLM for triplet extraction...")
        batch_results = client.create(
            response_model=BatchExtraction,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze these posts:\n\n{formatted_posts}"}
            ],
            max_retries=2,
            max_tokens=16000
        )
        end_llm = time.time()
        print(f"Time for LLM extraction of batch with {len(posts)} posts: {end_llm - start_llm:.2f} seconds")
        return batch_results

        
    except Exception as exc:
        end_llm = time.time()
        print(f"Time until LLM extraction failure: {end_llm - start_llm:.2f} seconds")
        print(f"Failed to extract triplets: {exc}")
        # Return empty results to avoid breaking the pipeline
        return BatchExtraction(results=[PostAnalysis(post_id=p['id'], has_business_info=False, justification="Error") for p in posts])

async def get_llm_triplets_async(posts: list[dict]) -> BatchExtraction:
    return await asyncio.to_thread(get_llm_triplets, posts)

async def run_parallel_extraction():
    # 1. Fetch data
    start_fetch = time.time()
    all_posts = await fetch_all_posts()
    end_fetch = time.time()
    print(f"Time to fetch all posts: {end_fetch - start_fetch:.2f} seconds")
    batch_size = 25
    
    # 2. Create batches
    batches = [all_posts[i:i + batch_size] for i in range(0, len(all_posts), batch_size)]
    
    print(f"Starting extraction for {len(all_posts)} posts in {len(batches)} batches...")

    # 3. Execute all batches concurrently
    # This will trigger 20 simultaneous API requests (1000 / 50)
    tasks = []
    for batch in batches:
        task = get_llm_triplets_async(batch)
        tasks.append(task)
    results = await asyncio.gather(*tasks)

    # 4. Flatten and process results
    all_extractions = []
    for batch_result in results:
        all_extractions.extend(batch_result.results)

    print(f"Successfully processed {len(all_extractions)} post analyses.")
    end_process = time.time()
    print(f"Total time for extraction process: {end_process - start_fetch:.2f} seconds")
    
    # Write results to JSON file
    with open("extraction_results.json", "w") as f:
        json.dump([item.model_dump() for item in all_extractions], f, indent=2)
    print("Results written to extraction_results.json")
    
    return all_extractions

def format_posts_for_llm(posts: list) -> str:
    batch_str = "<batch>\n"
    
    for p in posts:
        # Minify the text before adding to batch
        clean_content = minify_text(p['text'])
        
        batch_str += (
            f'  <post id="{p["id"]}">\n'
            f'    <url>{p["url"]}</url>\n'
            f'    <content>{clean_content}</content>\n'
            f'  </post>\n'
        )
        
    batch_str += "</batch>"
    return batch_str

def minify_text(text: str) -> str:
    if not text:
        return ""
    
    # 1. Remove Emojis (removes all non-BMP characters)
    # This effectively strips most emojis and special symbols
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    # 2. Normalize Whitespace & Newlines
    # Replace multiple newlines or tabs with a single space to flatten the text
    text = re.sub(r'\s+', ' ', text)

    
    return text.strip()