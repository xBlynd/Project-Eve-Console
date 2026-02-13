"""File Indexer Service for EVE Project Console"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from sqlalchemy.orm import Session

from backend.database import Library, FileEntry


def determine_file_kind(ext: str, config: dict) -> str:
    """Determine file kind based on extension"""
    ext_lower = ext.lower()
    
    for kind, extensions in config.get("file_extensions", {}).items():
        if ext_lower in extensions:
            return kind
    
    return "other"


def scan_library(root_path: str, config: dict) -> List[Dict]:
    """Recursively scan a directory and return file entries"""
    entries = []
    root = Path(root_path)
    
    # Get all supported extensions
    supported_exts = set()
    for exts in config.get("file_extensions", {}).values():
        supported_exts.update(exts)
    
    try:
        for file_path in root.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                
                # Only index supported file types
                if ext not in supported_exts:
                    continue
                
                try:
                    stat = file_path.stat()
                    rel_path = str(file_path.relative_to(root))
                    
                    entry = {
                        "path": str(file_path),
                        "rel_path": rel_path,
                        "ext": ext,
                        "size_bytes": stat.st_size,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime),
                        "kind": determine_file_kind(ext, config),
                    }
                    entries.append(entry)
                except (OSError, ValueError) as e:
                    # Skip files we can't access
                    continue
    
    except Exception as e:
        raise RuntimeError(f"Failed to scan library: {str(e)}")
    
    return entries


def index_library(db: Session, library_id: str, root_path: str, config: dict) -> int:
    """Index a library's files into the database"""
    # Get library
    library = db.query(Library).filter(Library.id == library_id).first()
    if not library:
        raise ValueError("Library not found")
    
    # Delete existing file entries for this library
    db.query(FileEntry).filter(FileEntry.library_id == library_id).delete()
    db.commit()
    
    # Scan directory
    file_entries = scan_library(root_path, config)
    
    # Insert new entries
    for entry in file_entries:
        db_entry = FileEntry(
            library_id=library_id,
            path=entry["path"],
            rel_path=entry["rel_path"],
            ext=entry["ext"],
            size_bytes=entry["size_bytes"],
            last_modified=entry["last_modified"],
            kind=entry["kind"],
        )
        db.add(db_entry)
    
    # Update library metadata
    library.file_count = len(file_entries)
    library.last_indexed = datetime.utcnow()
    db.commit()
    
    return len(file_entries)
