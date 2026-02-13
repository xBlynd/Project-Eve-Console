"""Pydantic Models for EVE Project Console"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
import uuid


# Library Models
class LibraryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    root_path: str = Field(..., min_length=1)
    type: Literal["project", "library"] = "project"
    tags: Optional[List[str]] = []


class LibraryResponse(BaseModel):
    id: str
    name: str
    root_path: str
    type: str
    tags: List[str]
    file_count: int
    last_indexed: Optional[datetime]
    
    class Config:
        from_attributes = True


# Query Models
class QueryRequest(BaseModel):
    library_id: str
    role: Literal["construction", "dev"]
    question: str = Field(..., min_length=1)
    keywords: List[str] = []
    max_files: int = Field(10, ge=1, le=50)


class QueryResponse(BaseModel):
    answer: str
    used_files: List[dict]


# Index Response
class IndexResponse(BaseModel):
    library_id: str
    file_count: int
    message: str
