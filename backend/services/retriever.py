"""File Retrieval Service for EVE Project Console"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import os

from backend.database import FileEntry

# PDF text extraction
try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PyPDF2 not installed. PDF text extraction disabled.")


def extract_file_content(file_path: str, file_ext: str) -> Optional[str]:
    """Extract text content from various file types"""
    
    # PDF extraction
    if file_ext.lower() == '.pdf' and PDF_SUPPORT:
        try:
            reader = PdfReader(file_path)
            text_parts = []
            
            # Extract text from all pages
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text.strip():
                    text_parts.append(f"\n--- PAGE {page_num} ---\n")
                    text_parts.append(page_text)
            
            full_text = ''.join(text_parts)
            return full_text if full_text.strip() else None
            
        except Exception as e:
            print(f"Failed to extract PDF {file_path}: {e}")
            return None
    
    # Text-based files
    text_extensions = [
        '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss',
        '.md', '.txt', '.json', '.yaml', '.yml', '.xml', '.csv',
        '.sh', '.bash', '.ps1', '.cs', '.java', '.cpp', '.c', '.h',
        '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.sql'
    ]
    
    if file_ext.lower() in text_extensions:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"Failed to read text file {file_path}: {e}")
            return None
    
    # Unsupported file type
    return None


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
    
    print(f"\n=== FILE RETRIEVAL DEBUG ===")
    print(f"Total files in library: {len(files)}")
    print(f"Keywords: {keywords}")
    print(f"Max files: {max_files}")
    
    # Score files based on keyword matches
    scored_files = []
    for file_entry in files:
        score = 0
        
        # Score based on keywords in filename/path
        filename_lower = file_entry.rel_path.lower()
        
        if keywords:
            for keyword in keywords:
                if keyword.lower() in filename_lower:
                    score += 10
                    print(f"  ✓ {file_entry.rel_path} matched keyword '{keyword}'")
        else:
            # No keywords = prioritize PDFs and docs
            if file_entry.ext.lower() in ['.pdf', '.md', '.txt', '.doc', '.docx']:
                score = 10
            else:
                score = 5
        
        # Boost important file types
        if file_entry.ext.lower() == '.pdf':
            score += 15  # PDFs are critical for construction docs
        elif file_entry.kind in ["code", "doc"]:
            score += 5
        
        # Penalize very large files
        if file_entry.size_bytes > 1000000:  # 1MB
            score -= 3
        
        if score > 0:
            scored_files.append((score, file_entry))
    
    # Sort by score (descending)
    scored_files.sort(key=lambda x: x[0], reverse=True)
    
    print(f"\nTop scored files:")
    for score, file_entry in scored_files[:10]:
        print(f"  Score {score}: {file_entry.rel_path} ({file_entry.ext})")
    
    # Select top files up to max_chars limit
    max_chars = config.get("default_max_chars", 30000)
    selected_files = []
    total_chars = 0
    
    for score, file_entry in scored_files:
        if len(selected_files) >= max_files:
            break
        
        print(f"\nProcessing: {file_entry.rel_path}")
        
        # Extract file content
        content = extract_file_content(file_entry.path, file_entry.ext)
        
        if content and content.strip():
            content_len = len(content)
            print(f"  Extracted {content_len} chars")
            
            # Check if adding this file would exceed char limit
            if total_chars + content_len > max_chars:
                remaining_space = max_chars - total_chars
                if remaining_space > 2000:  # Only add if we have reasonable space
                    content = content[:remaining_space] + "\n\n[CONTENT TRUNCATED TO FIT CONTEXT LIMIT]\n"
                    print(f"  Truncated to {len(content)} chars")
                else:
                    print(f"  Skipped - would exceed context limit")
                    break
            
            selected_files.append({
                "rel_path": file_entry.rel_path,
                "content": content,
                "ext": file_entry.ext,
                "kind": file_entry.kind,
            })
            
            total_chars += len(content)
            print(f"  Added! Total context: {total_chars} chars")
        else:
            print(f"  Failed to extract content or empty file")
    
    print(f"\n=== SELECTED {len(selected_files)} FILES ===")
    for f in selected_files:
        print(f"  - {f['rel_path']} ({len(f['content'])} chars)")
    print(f"=== END DEBUG ===\n")
    
    return selected_files
