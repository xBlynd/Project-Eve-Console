"""File Retrieval Service for EVE Project Console"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import os

from backend.database import FileEntry


def find_relevant_files(
    db: Session,
    library_id: str,
    keywords: List[str],
    max_files: int,
    config: dict,
) -> List[Dict[str, str]]:
    """Find and return relevant files based on keywords and filters"""
    
    # Query all files for this library
    files = db.query(FileEntry).filter(
        FileEntry.library_id == library_id
    ).all()
    
    if not files:
        return []
    
    # Score files based on keyword matches
    scored_files = []
    for file_entry in files:
        score = 0
        
        # Score based on keywords in filename/path
        if keywords:
            filename_lower = file_entry.rel_path.lower()
            for keyword in keywords:
                if keyword.lower() in filename_lower:
                    score += 10
        else:
            # No keywords = all files get base score
            score = 1
        
        # Boost code and doc files
        if file_entry.kind in ["code", "doc"]:
            score += 5
        
        # Penalize very large files (harder to process)
        if file_entry.size_bytes > 500000:  # 500KB
            score -= 5
        
        scored_files.append((score, file_entry))
    
    # Sort by score (descending)
    scored_files.sort(key=lambda x: x[0], reverse=True)
    
    # Select top files up to max_chars limit
    max_chars = config.get("default_max_chars", 20000)
    selected_files = []
    total_chars = 0
    
    for score, file_entry in scored_files:
        if len(selected_files) >= max_files:
            break
        
        # Try to read file content
        try:
            with open(file_entry.path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
                # Check if adding this file would exceed char limit
                if total_chars + len(content) > max_chars:
                    # Truncate content to fit
                    remaining_space = max_chars - total_chars
                    if remaining_space > 1000:  # Only add if we have reasonable space
                        content = content[:remaining_space] + "\n[TRUNCATED]\n"
                    else:
                        break
                
                selected_files.append({
                    "rel_path": file_entry.rel_path,
                    "content": content,
                    "ext": file_entry.ext,
                    "kind": file_entry.kind,
                })
                
                total_chars += len(content)
        
        except (OSError, UnicodeDecodeError):
            # Skip files we can't read
            continue
    
    return selected_files
