"""File Retrieval Service for EVE Project Console"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import os
import re

from backend.database import FileEntry

# PDF text extraction with PyMuPDF (superior to PyPDF2)
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("WARNING: PyMuPDF not installed. Run: pip install PyMuPDF")


def extract_file_content(file_path: str, file_ext: str) -> Optional[str]:
    """Extract text content from various file types"""
    
    # PDF extraction using PyMuPDF (handles scanned docs, tables, complex layouts)
    if file_ext.lower() == '.pdf' and PDF_SUPPORT:
        try:
            doc = fitz.open(file_path)
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"\n=== PAGE {page_num + 1} ===\n")
                    text_parts.append(page_text)
            
            doc.close()
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
    
    return None


def search_content_for_keywords(content: str, keywords: List[str]) -> int:
    """Search actual file CONTENT for keywords, return match score"""
    if not content or not keywords:
        return 0
    
    content_lower = content.lower()
    score = 0
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        # Count occurrences (each match = +5 points)
        count = content_lower.count(keyword_lower)
        if count > 0:
            score += min(count * 5, 50)  # Cap at 50 points per keyword
    
    return score


def calculate_file_score(file_entry: FileEntry, keywords: List[str], file_content: Optional[str] = None) -> int:
    """Calculate relevance score based on filename AND content"""
    score = 0
    filename_lower = file_entry.rel_path.lower()
    
    # Critical file types get base boost
    critical_patterns = [
        'lease', 'contract', 'agreement', 'work letter', 'workletter', 'work ltr',
        'landlord', 'tenant', 'proposal', 'specifications', 'specs',
        'drawings', 'plans', 'schedule', 'budget', 'rfp', 'bid'
    ]
    
    for pattern in critical_patterns:
        if pattern in filename_lower:
            score += 20
            print(f"  📄 {file_entry.rel_path}: filename matches '{pattern}' (+20)")
    
    # Keyword matching in filename
    if keywords:
        for keyword in keywords:
            if keyword.lower() in filename_lower:
                score += 10
                print(f"  🔍 {file_entry.rel_path}: filename contains '{keyword}' (+10)")
    
    # CONTENT SEARCH (the real magic)
    if file_content and keywords:
        content_score = search_content_for_keywords(file_content, keywords)
        if content_score > 0:
            score += content_score
            print(f"  ✨ {file_entry.rel_path}: CONTENT matches keywords (+{content_score})")
    
    # File type boosts
    if file_entry.ext.lower() == '.pdf':
        score += 10
    elif file_entry.ext.lower() in ['.docx', '.doc']:
        score += 8
    
    return score


def find_relevant_files(
    db: Session,
    library_id: str,
    keywords: List[str],
    max_files: int,
    config: dict,
) -> List[Dict[str, str]]:
    """Find files by searching ACTUAL CONTENT, not just filenames"""
    
    files = db.query(FileEntry).filter(FileEntry.library_id == library_id).all()
    
    if not files:
        return []
    
    print(f"\n{'='*70}")
    print(f"🔎 INTELLIGENT FILE SEARCH")
    print(f"{'='*70}")
    print(f"Total files: {len(files)}")
    print(f"Search keywords: {keywords}")
    print(f"\n📊 ANALYZING FILES (reading content)...\n")
    
    # Extract content and score ALL files
    scored_files = []
    
    for file_entry in files:
        # Extract content FIRST (so we can search it)
        content = extract_file_content(file_entry.path, file_entry.ext)
        
        if content:
            # Score based on filename AND content
            score = calculate_file_score(file_entry, keywords, content)
            
            if score > 0:
                scored_files.append((score, file_entry, content))
        else:
            # File couldn't be read, give minimal score if it matches filename
            score = calculate_file_score(file_entry, keywords, None)
            if score > 0:
                scored_files.append((score, file_entry, None))
    
    # Sort by score
    scored_files.sort(key=lambda x: x[0], reverse=True)
    
    print(f"\n{'='*70}")
    print(f"🏆 TOP RANKED FILES:")
    print(f"{'='*70}")
    for i, (score, file_entry, _) in enumerate(scored_files[:10], 1):
        print(f"{i:2}. Score {score:4} - {file_entry.rel_path}")
    
    # Select top files within context limit
    max_chars = config.get("default_max_chars", 30000)
    selected_files = []
    total_chars = 0
    
    print(f"\n{'='*70}")
    print(f"📦 BUILDING CONTEXT (max {max_chars:,} chars)")
    print(f"{'='*70}\n")
    
    for score, file_entry, content in scored_files:
        if len(selected_files) >= max_files:
            print(f"⚠️ Reached max_files limit ({max_files})")
            break
        
        if not content:
            print(f"⚠️ {file_entry.rel_path} - no content extracted, skipping")
            continue
        
        content_len = len(content)
        
        if total_chars + content_len > max_chars:
            remaining = max_chars - total_chars
            if remaining > 2000:
                content = content[:remaining] + "\n[TRUNCATED - CONTEXT LIMIT]\n"
                print(f"✂️ {file_entry.rel_path} - truncated to fit")
            else:
                print(f"❌ {file_entry.rel_path} - skipped (would exceed limit)")
                break
        
        selected_files.append({
            "rel_path": file_entry.rel_path,
            "content": content,
            "ext": file_entry.ext,
            "kind": file_entry.kind,
        })
        
        total_chars += len(content)
        print(f"✅ {file_entry.rel_path} ({len(content):,} chars)")
    
    print(f"\n{'='*70}")
    print(f"📤 SENDING TO EVE:")
    print(f"{'='*70}")
    print(f"Files: {len(selected_files)}")
    print(f"Total context: {total_chars:,} characters")
    print(f"{'='*70}\n")
    
    return selected_files
