"""Shared LLM utility used by both discovery and inference engines."""

import os
import asyncio
from typing import TypeVar, Type

import instructor
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def call_llm(
    response_model: Type[T],
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    max_retries: int = 2,
    max_tokens: int = 8000,
) -> T:
    """
    Make a structured LLM call and return a validated Pydantic model.

    Args:
        response_model: Pydantic model class for the expected response.
        system_prompt: System message content.
        user_prompt: User message content.
        model: Override for the LLM model identifier.
        max_retries: Number of retries on failure.
        max_tokens: Maximum tokens in the response.

    Returns:
        An instance of *response_model* populated by the LLM.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = model or os.getenv(
        "TRIPLET_EXTRACTOR_MODEL", "openrouter/google/gemini-2.0-flash-001"
    )

    mode = instructor.Mode.OPENROUTER_STRUCTURED_OUTPUTS
    client = instructor.from_provider(model, api_key=api_key, mode=mode)

    return client.create(
        response_model=response_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_retries=max_retries,
        max_tokens=max_tokens,
    )


async def call_llm_async(
    response_model: Type[T],
    system_prompt: str,
    user_prompt: str,
    **kwargs,
) -> T:
    """Async wrapper for :func:`call_llm`."""
    return await asyncio.to_thread(
        call_llm, response_model, system_prompt, user_prompt, **kwargs
    )
