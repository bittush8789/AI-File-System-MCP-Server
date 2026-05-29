import os
import shutil
import re
import zipfile
import json
from pathlib import Path
from typing import List, Dict, Any
from backend.utils.security import validate_path, get_relative_path, WORKSPACE_DIR
from backend.database import db

def read_file(path: str) -> str:
    """Reads and returns the content of a file within the workspace."""
    target_path = validate_path(path)
    if not target_path.is_file():
        raise FileNotFoundError(f"File not found or is not a file: {path}")
    with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    return content

def write_file(path: str, content: str) -> str:
    """Writes content to a file in the workspace, registering it in the DB."""
    target_path = validate_path(path)
    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    # Register file in DB
    relative_path = get_relative_path(target_path)
    db.register_file(relative_path)
    return f"Successfully wrote to {relative_path}"

def create_folder(path: str) -> str:
    """Creates a new folder inside the workspace."""
    target_path = validate_path(path)
    target_path.mkdir(parents=True, exist_ok=True)
    return f"Successfully created directory: {get_relative_path(target_path)}"

def delete_path(path: str) -> str:
    """Deletes a file or directory inside the workspace."""
    target_path = validate_path(path)
    if not target_path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    
    relative_path = get_relative_path(target_path)
    if target_path.is_dir():
        shutil.rmtree(target_path)
        # Remove all matching subfiles from DB
        all_files = db.get_all_files()
        for f in all_files:
            if f.startswith(relative_path):
                db.remove_file(f)
        return f"Successfully deleted folder: {relative_path}"
    else:
        target_path.unlink()
        db.remove_file(relative_path)
        return f"Successfully deleted file: {relative_path}"

def rename_path(old_path: str, new_path: str) -> str:
    """Renames a file or folder inside the workspace."""
    old_target = validate_path(old_path)
    new_target = validate_path(new_path)
    
    if not old_target.exists():
        raise FileNotFoundError(f"Source path not found: {old_path}")
    if new_target.exists():
        raise FileExistsError(f"Destination path already exists: {new_path}")
        
    # Ensure destination parent exists
    new_target.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.move(str(old_target), str(new_target))
    
    old_rel = get_relative_path(old_target)
    new_rel = get_relative_path(new_target)
    
    # Update database
    if old_target.is_file():
        db.remove_file(old_rel)
        db.register_file(new_rel)
    else:
        # It's a directory, update all file entries under it
        all_files = db.get_all_files()
        for f in all_files:
            if f.startswith(old_rel):
                db.remove_file(f)
                new_f_rel = f.replace(old_rel, new_rel, 1)
                db.register_file(new_f_rel)
                
    return f"Successfully moved/renamed from {old_rel} to {new_rel}"

def list_workspace(path: str = "") -> List[Dict[str, Any]]:
    """Lists files and folders inside a given directory in the workspace."""
    target_dir = validate_path(path)
    if not target_dir.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")
        
    items = []
    for item in target_dir.iterdir():
        rel_path = get_relative_path(item)
        items.append({
            "name": item.name,
            "path": rel_path,
            "is_dir": item.is_dir(),
            "size": item.stat().st_size if item.is_file() else 0,
            "modified": item.stat().st_mtime
        })
    return items

def search_files(query: str) -> List[Dict[str, Any]]:
    """Searches workspace files by path/name or contents."""
    results = []
    # Log search in history
    db.log_search(query)
    
    # Simple recursive search
    for root, _, files in os.walk(WORKSPACE_DIR):
        for file in files:
            file_path = Path(root) / file
            rel_path = get_relative_path(file_path)
            
            # Check filename match
            if query.lower() in file.lower() or query.lower() in rel_path.lower():
                results.append({
                    "path": rel_path,
                    "type": "filename_match",
                    "preview": ""
                })
                continue
                
            # Check content match (for text files)
            if file_path.suffix in ['.py', '.js', '.ts', '.md', '.txt', '.yaml', '.yml', '.json', '.html', '.css']:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_idx, line in enumerate(f, 1):
                            if query.lower() in line.lower():
                                results.append({
                                    "path": rel_path,
                                    "type": "content_match",
                                    "line": line_idx,
                                    "preview": line.strip()
                                })
                                if len(results) >= 50: # Limit matches
                                    break
                except Exception:
                    pass
            if len(results) >= 50:
                break
    return results

def count_classes_functions(file_path: Path) -> tuple[int, int]:
    """Helper to parse Python file to count classes and functions."""
    if file_path.suffix != ".py":
        return 0, 0
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        classes = len(re.findall(r"^\s*class\s+\w+", content, re.MULTILINE))
        functions = len(re.findall(r"^\s*def\s+\w+", content, re.MULTILINE))
        return classes, functions
    except Exception:
        return 0, 0

def summarize_codebase() -> Dict[str, Any]:
    """Gathers overall codebase metrics and updates files index in the database."""
    total_files = 0
    total_folders = 0
    total_classes = 0
    total_functions = 0
    file_types = {}
    largest_files = []
    
    for root, dirs, files in os.walk(WORKSPACE_DIR):
        # Ignore common directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.chroma']]
        total_folders += len(dirs)
        
        for file in files:
            file_path = Path(root) / file
            rel_path = get_relative_path(file_path)
            
            # Register in database
            db.register_file(rel_path)
            
            total_files += 1
            suffix = file_path.suffix or "unknown"
            file_types[suffix] = file_types.get(suffix, 0) + 1
            
            size = file_path.stat().st_size
            largest_files.append({"path": rel_path, "size": size})
            
            classes, functions = count_classes_functions(file_path)
            total_classes += classes
            total_functions += functions
            
    largest_files.sort(key=lambda x: x["size"], reverse=True)
    
    return {
        "total_files": total_files,
        "total_folders": total_folders + 1, # include root
        "total_classes": total_classes,
        "total_functions": total_functions,
        "file_types": file_types,
        "largest_files": largest_files[:5]
    }

def generate_docs() -> Dict[str, str]:
    """Generates standard README, API_DOCS, and ARCHITECTURE markdown templates."""
    docs = {
        "README.md": """# Workspace Project

## Overview
This is a standard project workspace managed by AI File System MCP.

## Getting Started
To get started:
1. Run application components or setup dependencies.
2. Explore codebase using AI Chat Assistant.
""",
        "API_DOCS.md": """# API Documentation

## Health Check
- **Endpoint:** `/health`
- **Method:** `GET`
- **Description:** Returns backend status.

## Operations
- **Endpoint:** `/read-file` - Reads workspace files.
- **Endpoint:** `/write-file` - Writes content to a workspace file.
- **Endpoint:** `/semantic-search` - Performs similarity vector search on code.
""",
        "ARCHITECTURE.md": """# Architecture Overview

## Tech Stack
- Frontend: Streamlit
- Backend: FastAPI, MCP SDK
- Vector DB: ChromaDB
- Metadata DB: SQLite
- AI Layer: LangChain
"""
    }
    
    # Auto write these files in a "docs/" directory in the workspace
    docs_dir = WORKSPACE_DIR / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    written_paths = {}
    for filename, content in docs.items():
        doc_path = docs_dir / filename
        doc_path.write_text(content, encoding="utf-8")
        rel_path = get_relative_path(doc_path)
        db.register_file(rel_path)
        db.log_generated_doc(filename)
        written_paths[filename] = rel_path
        
    return written_paths


def extract_zip_to_workspace(zip_path_or_bytes) -> int:
    """Safely extracts a ZIP archive into the workspace sandbox after clearing it."""
    # 1. Clear current workspace
    for item in WORKSPACE_DIR.iterdir():
        if item.name in ['.git', '.chroma']:
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        except Exception:
            pass
            
    # 2. Extract ZIP contents
    extracted_count = 0
    with zipfile.ZipFile(zip_path_or_bytes) as z:
        for member in z.infolist():
            member_path = Path(member.filename)
            # Prevent zip slip/directory traversal
            if member_path.is_absolute() or ".." in member_path.parts:
                continue
            
            target_path = (WORKSPACE_DIR / member_path).resolve()
            try:
                target_path.relative_to(WORKSPACE_DIR)
            except ValueError:
                continue
                
            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "wb") as f:
                    f.write(z.read(member))
                extracted_count += 1
                
                # Register in SQLite database
                rel_path = get_relative_path(target_path)
                db.register_file(rel_path)
                
    return extracted_count


# Secrets & Key Patterns
SECRET_PATTERNS = {
    "Generic API Key": r"(?:key|api_key|apikey|secret|token|password|auth|passwd|cred)\s*=\s*['\"][a-zA-Z0-9_\-+=]{16,}['\"]",
    "OpenAI API Key": r"sk-[a-zA-Z0-9]{32,}",
    "Gemini API Key": r"AIzaSy[a-zA-Z0-9_\-]{33}",
    "Slack Token": r"xox[bapr]-[a-zA-Z0-9-]{10,}",
    "AWS Access Key ID": r"AKIA[0-9A-Z]{16}",
    "AWS Secret Access Key": r"aws_secret_access_key\s*=\s*['\"][a-zA-Z0-9+/=]{40}['\"]",
    "Database Credentials": r"mongodb(?:\+srv)?://|postgres://|mysql://|redis://"
}

def scan_security() -> List[Dict[str, Any]]:
    """Performs a static security scan of the codebase to detect secrets, keys, and insecure settings."""
    findings = []
    for root, dirs, files in os.walk(WORKSPACE_DIR):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.chroma']]
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix in ['.py', '.js', '.ts', '.json', '.env', '.yaml', '.yml', '.txt', '.ini', '.conf']:
                try:
                    rel_path = get_relative_path(file_path)
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    for idx, line in enumerate(lines, 1):
                        for name, pattern in SECRET_PATTERNS.items():
                            if re.search(pattern, line, re.IGNORECASE):
                                findings.append({
                                    "file": rel_path,
                                    "line": idx,
                                    "issue": f"Possible {name} detected",
                                    "severity": "High" if name != "Generic API Key" else "Medium",
                                    "snippet": line.strip()[:60] + "..."
                                })
                except Exception:
                    pass
    return findings


def analyze_dependencies() -> Dict[str, Any]:
    """Scans and parses the project dependency files."""
    dependencies = []
    
    # 1. Parse requirements.txt
    req_file = WORKSPACE_DIR / "requirements.txt"
    if req_file.exists():
        try:
            content = req_file.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    # split package name and version comparison operators
                    parts = re.split(r'[=<>~!]', line)
                    pkg = parts[0].strip()
                    version = line[len(pkg):].strip() or "Latest"
                    dependencies.append({"name": pkg, "version": version, "file": "requirements.txt"})
        except Exception:
            pass
            
    # 2. Parse package.json
    pkg_file = WORKSPACE_DIR / "package.json"
    if pkg_file.exists():
        try:
            content = pkg_file.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(content)
            for dep_type in ["dependencies", "devDependencies"]:
                for pkg, version in data.get(dep_type, {}).items():
                    dependencies.append({"name": pkg, "version": version, "file": "package.json"})
        except Exception:
            pass
            
    # Heuristics for outdated and unused dependencies
    outdated = []
    unused = []
    for d in dependencies:
        # Flag outdated heuristically for common packages
        clean_v = re.sub(r'[^\d.]', '', d["version"])
        if clean_v and clean_v.startswith(("0.", "1.", "2.")):
            outdated.append({"name": d["name"], "current": d["version"], "latest": "3.9.0"})
            
        # Detect if it's unused (heuristic: not imported or referenced in files)
        is_used = False
        for root, dirs, files in os.walk(WORKSPACE_DIR):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.chroma']]
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix in ['.py', '.js', '.ts'] and file_path.name not in ["requirements.txt", "package.json"]:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        # Match simple word boundaries
                        if re.search(r'\b' + re.escape(d["name"].replace('-', '_')) + r'\b', content, re.IGNORECASE):
                            is_used = True
                            break
                    except Exception:
                        pass
            if is_used:
                break
        if not is_used:
            unused.append(d["name"])
            
    return {
        "list": dependencies,
        "outdated": outdated,
        "unused": unused
    }


def scan_project_architecture() -> Dict[str, Any]:
    """Performs codebase architecture scan including routes, database usage, frameworks."""
    apis = []
    db_usage = []
    frameworks = []
    project_type = "Unknown"
    
    all_files = []
    for root, dirs, files in os.walk(WORKSPACE_DIR):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.chroma']]
        for f in files:
            all_files.append(Path(root) / f)
            
    has_python = False
    has_js = False
    
    for f in all_files:
        ext = f.suffix.lower()
        if ext == ".py":
            has_python = True
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            has_js = True
            
        if ext in [".py", ".js", ".ts"]:
            try:
                rel = get_relative_path(f)
                content = f.read_text(encoding="utf-8", errors="ignore")
                
                # Check Framework markers
                if "fastapi" in content.lower() and "FastAPI" not in frameworks:
                    frameworks.append("FastAPI")
                if "flask" in content.lower() and "Flask" not in frameworks:
                    frameworks.append("Flask")
                if "django" in content.lower() and "Django" not in frameworks:
                    frameworks.append("Django")
                if "express" in content.lower() and "Express.js" not in frameworks:
                    frameworks.append("Express.js")
                if "react" in content.lower() and "React" not in frameworks:
                    frameworks.append("React")
                if "next" in content.lower() and "Next.js" not in frameworks:
                    frameworks.append("Next.js")
                    
                # Parse lines for specific routes or DB patterns
                for idx, line in enumerate(content.splitlines(), 1):
                    # Route markers
                    route_match = re.search(r"@\w+\.(?:get|post|put|delete|patch|route)\s*\(\s*['\"]([^'\"]+)['\"]", line)
                    if route_match:
                        apis.append({"path": route_match.group(1), "method": "GET/POST", "file": rel, "line": idx})
                    # Express route markers
                    express_match = re.search(r"\.(?:get|post|put|delete)\s*\(\s*['\"]([^'\"]+)['\"]", line)
                    if express_match and has_js:
                        apis.append({"path": express_match.group(1), "method": "GET/POST", "file": rel, "line": idx})
                        
                    # DB markers
                    for db_key in ["sqlite", "postgresql", "mysql", "mongodb", "redis", "prisma", "sqlalchemy", "pymongo"]:
                        if db_key in line.lower():
                            db_entry = f"{db_key.capitalize()} reference found at {rel}:{idx}"
                            if db_entry not in db_usage:
                                db_usage.append(db_entry)
            except Exception:
                pass
                
    if has_python:
        project_type = "Python Ecosystem"
    elif has_js:
        project_type = "Node.js / Frontend Ecosystem"
        
    arch_pattern = "Monolithic / Standard Architecture"
    # Check folder name architecture patterns
    folder_names = [d.lower() for root, dirs, _ in os.walk(WORKSPACE_DIR) for d in dirs]
    if "controllers" in folder_names or "models" in folder_names or "views" in folder_names:
        arch_pattern = "MVC (Model-View-Controller)"
    elif "services" in folder_names or "repositories" in folder_names:
        arch_pattern = "Service Layer / Repository Pattern"
    elif "components" in folder_names and "pages" in folder_names:
        arch_pattern = "Component-Based Architecture (Next.js/React)"
        
    return {
        "project_type": project_type,
        "frameworks": frameworks or ["Generic Ecosystem"],
        "architecture_pattern": arch_pattern,
        "apis": apis,
        "database_usage": db_usage
    }
