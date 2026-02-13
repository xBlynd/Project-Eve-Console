"""File Retrieval Service for EVE Project Console"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import os
import re

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


# Critical file name patterns for construction projects
CRITICAL_FILE_PATTERNS = [
    'lease', 'contract', 'agreement', 'work letter', 'workletter', 'work ltr',
    'landlord', 'tenant', 'proposal', 'specifications', 'specs',
    'drawings', 'plans', 'schedule', 'budget', 'estimate',
    'rfp', 'bid', 'scope', 'sow', 'statement of work'
]


def calculate_file_score(file_entry: FileEntry, keywords: List[str]) -> int:
    """Calculate relevance score for a file"""
    score = 0
    filename_lower = file_entry.rel_path.lower()
    
    # CRITICAL: Check for important construction document types
    for critical_pattern in CRITICAL_FILE_PATTERNS:
        if critical_pattern in filename_lower:
            score += 25  # Heavy boost for critical docs
            print(f"  ⭐ CRITICAL: {file_entry.rel_path} matches '{critical_pattern}' (+25)")
    
    # Keyword matching in filename
    if keywords:
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in filename_lower:
                score += 10
                print(f"  ✓ {file_entry.rel_path} matched keyword '{keyword}' (+10)")
    
    # File type boosts
    if file_entry.ext.lower() == '.pdf':
        score += 15  # PDFs are critical in construction
    elif file_entry.ext.lower() in ['.docx', '.doc']:
        score += 12
    elif file_entry.ext.lower() in ['.xlsx', '.xls', '.csv']:
        score += 8
    elif file_entry.kind == 'doc':
        score += 5
    
    # Penalize very large files slightly
    if file_entry.size_bytes > 2000000:  # 2MB
        score -= 3
    
    # Give all files a minimum score so they can be retrieved if needed
    if score == 0 and not keywords:
        score = 1
    
    return score


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
    
    print(f"\n{'='*70}")
    print(f"FILE RETRIEVAL ANALYSIS")
    print(f"{'='*70}")
    print(f"Total files in library: {len(files)}")
    print(f"Keywords: {keywords}")
    print(f"Max files requested: {max_files}")
    print(f"\nScoring files...")
    
    # Score all files
    scored_files = []
    for file_entry in files:
        score = calculate_file_score(file_entry, keywords)
        if score > 0:
            scored_files.append((score, file_entry))
    
    # Sort by score (descending)
    scored_files.sort(key=lambda x: x[0], reverse=True)
    
    print(f"\n{'='*70}")
    print(f"TOP SCORED FILES (showing top 15):")
    print(f"{'='*70}")
    for i, (score, file_entry) in enumerate(scored_files[:15], 1):
        print(f"{i:2}. Score {score:3}: {file_entry.rel_path}")
    
    # Select top files up to max_chars limit
    max_chars = config.get("default_max_chars", 30000)
    selected_files = []
    total_chars = 0
    
    print(f"\n{'='*70}")
    print(f"EXTRACTING CONTENT (max {max_chars} chars)")
    print(f"{'='*70}")
    
    for score, file_entry in scored_files:
        if len(selected_files) >= max_files:
            print(f"\n⚠️ Reached max_files limit ({max_files})")
            break
        
        # Extract file content
        content = extract_file_content(file_entry.path, file_entry.ext)
        
        if content and content.strip():
            content_len = len(content)
            
            # Check if adding this file would exceed char limit
            if total_chars + content_len > max_chars:
                remaining_space = max_chars - total_chars
                if remaining_space > 2000:  # Only add if we have reasonable space
                    content = content[:remaining_space] + "\n\n[CONTENT TRUNCATED - REACHED CONTEXT LIMIT]\n"
                    print(f"\n✂️ {file_entry.rel_path}")
                    print(f"   Truncated: {content_len} → {len(content)} chars")
                else:
                    print(f"\n❌ {file_entry.rel_path}")
                    print(f"   Skipped: would exceed context limit")
                    break
            else:
                print(f"\n✓ {file_entry.rel_path}")
                print(f"   Extracted: {content_len:,} chars")
            
            selected_files.append({
                "rel_path": file_entry.rel_path,
                "content": content,
                "ext": file_entry.ext,
                "kind": file_entry.kind,
            })
            
            total_chars += len(content)
        else:
            print(f"\n⚠️ {file_entry.rel_path}")
            print(f"   Failed to extract content")
    
    print(f"\n{'='*70}")
    print(f"FINAL SELECTION")
    print(f"{'='*70}")
    print(f"Selected files: {len(selected_files)}")
    print(f"Total context: {total_chars:,} characters")
    print(f"\nFiles being sent to EVE:")
    for i, f in enumerate(selected_files, 1):
        print(f"  {i}. {f['rel_path']} ({len(f['content']):,} chars)")
    print(f"{'='*70}\n")
    
    return selected_files
