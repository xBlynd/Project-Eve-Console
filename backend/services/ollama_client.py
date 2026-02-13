"""Ollama API Client for EVE Project Console"""

import httpx
from typing import List, Dict, Literal


async def query_eve(
    role: Literal["construction", "dev"],
    question: str,
    context_files: List[Dict[str, str]],
    config: dict,
) -> str:
    """Query EVE (via Ollama) with context from files"""
    
    # Select model based on role
    model = config["models"][role]
    
    # Build context string from files
    context_parts = []
    for i, file_data in enumerate(context_files, 1):
        context_parts.append(
            f"CONTEXT FILE {i}: {file_data['rel_path']}\n"
            f"----\n"
            f"{file_data['content']}\n\n"
        )
    
    context = "\n".join(context_parts)
    
    # Build the full prompt
    full_prompt = f"{context}\nUSER QUESTION:\n{question}"
    
    # Call Ollama API
    ollama_url = config.get("ollama_base_url", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get("response", "No response from EVE")
    
    except httpx.HTTPError as e:
        raise RuntimeError(f"Failed to connect to Ollama: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Query failed: {str(e)}")
