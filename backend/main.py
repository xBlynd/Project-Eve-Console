"""EVE Project Console - Main FastAPI Application"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import yaml
import os

from backend.models import (
    LibraryCreate,
    LibraryResponse,
    QueryRequest,
    QueryResponse,
    IndexResponse,
)
from backend.database import get_db, init_db, Library, FileEntry
from backend.services.indexer import scan_library, index_library
from backend.services.retriever import find_relevant_files
from backend.services.ollama_client import query_eve

# Load configuration
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

app = FastAPI(
    title="EVE Project Console",
    description="Local AI Operations Intelligence Layer for xsvStudio",
    version="1.0.0",
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Create storage directory if it doesn't exist
    os.makedirs("storage", exist_ok=True)


# Health check
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "EVE Project Console"}


# Library Management Endpoints
@app.post("/api/libraries", response_model=LibraryResponse)
def create_library(library: LibraryCreate, db: Session = Depends(get_db)):
    """Create a new library/project"""
    # Check if path exists
    if not os.path.exists(library.root_path):
        raise HTTPException(status_code=400, detail="Root path does not exist")
    
    # Check for duplicate paths
    existing = db.query(Library).filter(Library.root_path == library.root_path).first()
    if existing:
        raise HTTPException(status_code=400, detail="Library with this path already exists")
    
    # Create library entry
    db_library = Library(
        name=library.name,
        root_path=library.root_path,
        type=library.type,
        tags=library.tags or [],
    )
    db.add(db_library)
    db.commit()
    db.refresh(db_library)
    
    return db_library


@app.get("/api/libraries", response_model=List[LibraryResponse])
def list_libraries(db: Session = Depends(get_db)):
    """List all libraries"""
    libraries = db.query(Library).all()
    return libraries


@app.get("/api/libraries/{library_id}", response_model=LibraryResponse)
def get_library(library_id: str, db: Session = Depends(get_db)):
    """Get a specific library"""
    library = db.query(Library).filter(Library.id == library_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    return library


@app.delete("/api/libraries/{library_id}")
def delete_library(library_id: str, db: Session = Depends(get_db)):
    """Delete a library and its file entries"""
    library = db.query(Library).filter(Library.id == library_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    
    # Delete associated files
    db.query(FileEntry).filter(FileEntry.library_id == library_id).delete()
    db.delete(library)
    db.commit()
    
    return {"message": "Library deleted successfully"}


@app.post("/api/libraries/{library_id}/index", response_model=IndexResponse)
def index_library_endpoint(library_id: str, db: Session = Depends(get_db)):
    """Index or re-index a library's files"""
    library = db.query(Library).filter(Library.id == library_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    
    try:
        file_count = index_library(db, library_id, library.root_path, config)
        return {
            "library_id": library_id,
            "file_count": file_count,
            "message": f"Successfully indexed {file_count} files"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@app.get("/api/libraries/{library_id}/files")
def get_library_files(library_id: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get files in a library (for debugging/inspection)"""
    library = db.query(Library).filter(Library.id == library_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    
    files = db.query(FileEntry).filter(
        FileEntry.library_id == library_id
    ).offset(skip).limit(limit).all()
    
    return {
        "library_id": library_id,
        "total_files": library.file_count,
        "files": [
            {
                "rel_path": f.rel_path,
                "ext": f.ext,
                "kind": f.kind,
                "size_bytes": f.size_bytes,
                "last_modified": f.last_modified.isoformat(),
            }
            for f in files
        ]
    }


# Query Endpoint
@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(query: QueryRequest, db: Session = Depends(get_db)):
    """Ask EVE a question with context from library files"""
    # Validate library exists
    library = db.query(Library).filter(Library.id == query.library_id).first()
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    
    # Find relevant files
    try:
        relevant_files = find_relevant_files(
            db,
            query.library_id,
            query.keywords,
            query.max_files,
            config
        )
        
        if not relevant_files:
            return QueryResponse(
                answer="No relevant files found in this library. Please ensure the library has been indexed.",
                used_files=[]
            )
        
        # Query Ollama with context
        answer = await query_eve(
            role=query.role,
            question=query.question,
            context_files=relevant_files,
            config=config
        )
        
        return QueryResponse(
            answer=answer,
            used_files=[{"rel_path": f["rel_path"]} for f in relevant_files]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")
