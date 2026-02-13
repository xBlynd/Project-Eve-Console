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
    
    # Build the user message with context
    user_message = f"""I have provided you with the following files from my project:

{context}

Based on these files, please answer the following question:

{question}

Provide a clear, direct answer based ONLY on the content of the files provided. If the files don't contain relevant information to answer the question, say so."""
    
    # Call Ollama API using the chat endpoint
    ollama_url = config.get("ollama_base_url", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": user_message
                        }
                    ],
                    "stream": False,
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract the assistant's message from the response
            if "message" in result and "content" in result["message"]:
                return result["message"]["content"]
            else:
                return result.get("response", "No response from EVE")
    
    except httpx.HTTPError as e:
        raise RuntimeError(f"Failed to connect to Ollama: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Query failed: {str(e)}")
