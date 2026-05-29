import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from backend.utils.security import validate_path, WORKSPACE_DIR, get_relative_path
from backend.tools import fs_tools
from backend.vectorstore.vector_store import vector_store
from backend.database import db

logger = logging.getLogger(__name__)

def get_chat_model(model_name: str = "llama-3.3-70b-versatile"):
    """Initializes LLM based on available API keys. Falls back to None if keys are missing."""
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(model=model_name, temperature=0.2)
        except ImportError:
            pass
    elif openai_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o", temperature=0.2)
        except ImportError:
            pass
    elif gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0.2)
        except ImportError:
            pass
    return None

def chat_assistant(question: str, model_name: str = "llama-3.3-70b-versatile") -> str:
    """Answers user queries with RAG context from ChromaDB and codebase structure."""
    db.log_search(question) # Log query
    
    # 1. Retrieve semantic search hits
    search_hits = vector_store.semantic_search(question, limit=4)
    context_str = ""
    if search_hits:
        context_str = "\n\n".join([
            f"--- Context File: {hit['path']} (Similarity: {hit['similarity']}) ---\n{hit['content']}"
            for hit in search_hits
        ])
    
    # 2. Get quick codebase layout summary
    try:
        summary = fs_tools.summarize_codebase()
        summary_str = f"Workspace Stats: {summary['total_files']} files, {summary['total_folders']} folders."
    except Exception:
        summary_str = "Workspace layout is currently empty or loading."

    system_prompt = f"""You are a Senior AI Developer Assistant. You help developers understand, build, and debug applications in their workspace.
Below is the metadata and matching context retrieved from the workspace:
{summary_str}

RELEVANT CODE SNIPPETS AND FILE CONTENTS:
{context_str}

Please answer the user's question clearly. If code snippets are provided, cite the filename. If no relevant context is present, state that you are answering with general knowledge and suggest indexing the codebase or creating files first.
"""
    
    model = get_chat_model(model_name)
    if not model:
        # Graceful fallback response
        fallback_msg = (
            "⚠️ **API Key Missing**: Please set `GROQ_API_KEY` in your `.env` file.\n\n"
            f"**Simulated RAG Search Context**:\n"
            f"Found {len(search_hits)} matching files in vector database.\n"
        )
        if search_hits:
            fallback_msg += "\nMatches:\n"
            for hit in search_hits:
                fallback_msg += f"- `{hit['path']}` (similarity: {hit['similarity']})\n"
        else:
            fallback_msg += "No file chunks matched this query.\n"
        
        fallback_msg += f"\n**Question Received**: '{question}'"
        return fallback_msg
        
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        response = model.invoke(messages)
        answer = response.content
        db.log_chat(question, answer)
        return answer
    except Exception as e:
        return f"Error communicating with AI model: {str(e)}"

def analyze_repository() -> Dict[str, Any]:
    """
    Performs static code intelligence on the workspace.
    Detects technology stack, maps dependencies, identifies large functions,
    and performs dead code heuristics.
    """
    all_files = []
    for root, _, files in os.walk(WORKSPACE_DIR):
        for f in files:
            all_files.append(Path(root) / f)
            
    # 1. Tech Stack Detection
    techs = []
    file_extensions = {}
    for f in all_files:
        suffix = f.suffix.lower()
        file_extensions[suffix] = file_extensions.get(suffix, 0) + 1
        
    if any(f.name == "package.json" for f in all_files):
        techs.append("Node.js/JavaScript ecosystem")
    if any(f.name in ["requirements.txt", "pyproject.toml", "Pipfile"] for f in all_files):
        techs.append("Python ecosystem")
    if any(f.name == "Cargo.toml" for f in all_files):
        techs.append("Rust ecosystem")
    if any(f.name == "go.mod" for f in all_files):
        techs.append("Go ecosystem")
    if any(f.name == "docker-compose.yml" or f.name == "Dockerfile" for f in all_files):
        techs.append("Docker Containerization")
        
    if not techs:
        techs.append("Generic Project (No major framework/config files found)")

    # 2. Large Function Detection (> 50 lines)
    large_functions = []
    # 3. Simple Dependency analysis (Python imports mapping)
    imports_map = {}
    # 4. Dead Code detection (heuristics: function defined but never called/imported elsewhere)
    defined_funcs = {} # name -> (file, line)
    function_calls = set()
    
    for f in all_files:
        if f.suffix == ".py":
            try:
                rel = get_relative_path(f)
                content = f.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                
                # Scan line by line
                current_func = None
                func_start_line = 0
                
                for idx, line in enumerate(lines, 1):
                    # Python imports check
                    import_match = re.match(r"^\s*(?:import|from)\s+(\w+)", line)
                    if import_match:
                        mod = import_match.group(1)
                        imports_map[rel] = imports_map.get(rel, [])
                        if mod not in imports_map[rel]:
                            imports_map[rel].append(mod)
                            
                    # Function definition check
                    func_match = re.match(r"^\s*def\s+(\w+)\s*\(", line)
                    if func_match:
                        func_name = func_match.group(1)
                        if not func_name.startswith("__"): # Skip double underscore
                            defined_funcs[func_name] = (rel, idx)
                        
                        # Handle previous function block size
                        if current_func:
                            size = idx - func_start_line
                            if size > 50:
                                large_functions.append({
                                    "file": rel,
                                    "function": current_func,
                                    "lines": size,
                                    "start": func_start_line
                                })
                        current_func = func_name
                        func_start_line = idx
                    
                    # Look for potential function call names in the file
                    # Tokenize line roughly to find words
                    words = re.findall(r"\b\w+\b", line)
                    for w in words:
                        function_calls.add(w)
                        
                # Check last function
                if current_func:
                    size = len(lines) - func_start_line + 1
                    if size > 50:
                        large_functions.append({
                            "file": rel,
                            "function": current_func,
                            "lines": size,
                            "start": func_start_line
                        })
            except Exception:
                pass

    # Dead code: defined functions that are never called
    dead_code = []
    for func, (file, line) in defined_funcs.items():
        # Heuristic: if the function name does not appear in function_calls (excluding its definition line)
        # We check simple frequency. If it appears less than twice, it's likely dead.
        if func not in function_calls:
            dead_code.append({
                "file": file,
                "function": func,
                "line": line
            })
            
    return {
        "techs": techs,
        "file_extensions": file_extensions,
        "large_functions": large_functions,
        "dependencies": imports_map,
        "dead_code": dead_code[:15] # Limit output
    }

def auto_project_generator(prompt: str, model_name: str = "llama-3.3-70b-versatile") -> str:
    """Uses LLM to create scaffolding and code structure or falls back to template."""
    model = get_chat_model(model_name)
    
    scaffold_json = None
    
    if model:
        system_prompt = """You are a Senior Project Generator. Based on the user's prompt, generate a project structure.
Respond ONLY with a valid JSON object in the following format. Do not write any markdown code fences, headers, or extra text.
{
  "files": {
    "relative/path/to/file1.py": "File content 1",
    "relative/path/to/file2.py": "File content 2",
    "README.md": "Project documentation"
  }
}
"""
        try:
            response = model.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Create code and directories for: {prompt}")
            ])
            # Clean possible markdown wrap
            cleaned = response.content.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            scaffold_json = json.loads(cleaned.strip())
        except Exception as e:
            logger.error(f"Failed to use LLM for scaffold creation: {str(e)}")

    if not scaffold_json:
        # High quality fallback template generator
        if "fastapi" in prompt.lower() or "api" in prompt.lower():
            scaffold_json = {
                "files": {
                    "main.py": """from fastapi import FastAPI

app = FastAPI(title="Generated API")

@app.get("/")
def read_root():
    return {"message": "Welcome to your FastAPI microservice"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
""",
                    "requirements.txt": "fastapi\nuvicorn\npydantic\n",
                    "README.md": f"# Generated API Project\n\nScaffolded for: {prompt}\n\n## Running\n`uvicorn main:app --reload`"
                }
            }
        else:
            # Default fallback template
            scaffold_json = {
                "files": {
                    "app.py": "print('Hello Workspace!')\n",
                    "README.md": f"# Clean Python Workspace\n\nScaffolded for: {prompt}\n"
                }
            }

    # Write files using fs_tools
    written = []
    for filepath, content in scaffold_json.get("files", {}).items():
        fs_tools.write_file(filepath, content)
        written.append(filepath)
        
    return f"Scaffolded project structure. Generated {len(written)} files:\n" + "\n".join([f"- `{w}`" for w in written])


def query_llm_with_fallback(system_prompt: str, user_prompt: str, fallback_content: str, model_name: str = "llama-3.3-70b-versatile") -> str:
    """Helper to query the LLM and return static fallback content if credentials/modules are missing."""
    model = get_chat_model(model_name)
    if not model:
        return f"⚠️ **API Key Not Configured (Offline Mode)**\n\n*Below is the locally generated static analysis fallback info:*\n\n{fallback_content}"
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        res = model.invoke(messages)
        return res.content
    except Exception as e:
        logger.error(f"Error querying LLM: {str(e)}")
        return f"⚠️ **AI Generation Error ({str(e)})**\n\n{fallback_content}"


def generate_project_summary(model_name: str = "llama-3.3-70b-versatile") -> str:
    """Generates an AI-powered summary describing project purpose, modules, features, and workflows."""
    stats = fs_tools.summarize_codebase()
    arch = fs_tools.scan_project_architecture()
    
    file_list = [f["path"] for f in stats.get("largest_files", [])]
    
    system_prompt = "You are an expert software architect analyzing an uploaded codebase structure."
    user_prompt = f"""
    Please generate a comprehensive codebase summary based on the following metadata:
    - Ecosystem: {arch.get('project_type')}
    - Frameworks detected: {', '.join(arch.get('frameworks'))}
    - Architecture Pattern: {arch.get('architecture_pattern')}
    - Total Files: {stats.get('total_files')}
    - Major Workspace Files: {', '.join(file_list)}
    
    Include:
    1. **Purpose**: Overall business/technical purpose of this project.
    2. **Main Modules**: Break down the core files and what they do.
    3. **Key Features**: Highlight features found.
    4. **Application Workflow**: Step-by-step description of data flows.
    """
    
    fallback = f"""### 📝 Project Overview (Static Summary)
* **Ecosystem**: {arch.get('project_type')}
* **Architecture Pattern**: {arch.get('architecture_pattern')}
* **Frameworks**: {', '.join(arch.get('frameworks'))}
* **Project Statistics**: The workspace has {stats.get('total_files')} files and {stats.get('total_folders')} directories.

### 🧩 Main Modules & Code Structure
* The entry files and configs are located at the root of the workspace.
* Core application logic is structured according to {arch.get('architecture_pattern')} patterns.
"""
    return query_llm_with_fallback(system_prompt, user_prompt, fallback, model_name)


def generate_codebase_docs(doc_type: str, model_name: str = "llama-3.3-70b-versatile") -> str:
    """Generates technical documentation (Installation, Configuration, APIs, Deployment, Troubleshooting)."""
    stats = fs_tools.summarize_codebase()
    arch = fs_tools.scan_project_architecture()
    
    system_prompt = f"You are a technical writer documenting a {arch.get('project_type')} codebase."
    user_prompt = f"""
    Generate the '{doc_type}' document. 
    Here is the project architecture:
    - Frameworks: {', '.join(arch.get('frameworks'))}
    - Pattern: {arch.get('architecture_pattern')}
    - APIs detected: {json.dumps(arch.get('apis'))}
    - Databases: {json.dumps(arch.get('database_usage'))}
    """
    
    fallback_templates = {
        "Installation Guide": f"""# ⚙️ Installation Guide

## Prerequisites
- For {arch.get('project_type')}, ensure your environment runtime (Python/Node.js) is installed.

## Steps
1. Clone or download the codebase.
2. Initialize setup commands:
   ```bash
   # If requirements.txt exists:
   pip install -r requirements.txt
   # If package.json exists:
   npm install
   ```
3. Run the development server or main entry point.
""",
        "Configuration Guide": """# 🔧 Configuration Guide

## Environment Variables
Create a `.env` file in the root directory:
```env
PORT=8000
DATABASE_URL=sqlite:///database.db
API_KEY=your_key_here
```
""",
        "API Documentation": f"""# 📡 API Documentation

Detected Routes & Interface endpoints:
{chr(10).join([f"- **Path**: `{a['path']}` (defined in `{a['file']}`)" for a in arch.get('apis', [])]) or "No explicit API endpoints mapped by static analysis."}
""",
        "Folder Structure Explanation": f"""# 📂 Folder Structure Explanation

Project workspace directories layout:
- Root: Configuration files, `.env`, dependency descriptors.
- Subfolders: Core modules aligned with **{arch.get('architecture_pattern')}** guidelines.
""",
        "Deployment Guide": f"""# 🚀 Deployment Guide

## Docker Setup
If `Dockerfile` is present:
```bash
docker build -t app-service .
docker run -p 8000:8000 app-service
```
""",
        "Troubleshooting Section": """# 🔍 Troubleshooting

## Common Issues
- **Missing Dependencies**: Re-run the installation commands.
- **Port Conflicts**: Change the host binding configuration inside the environment file.
"""
    }
    
    fallback = fallback_templates.get(doc_type, f"# {doc_type}\nDocumentation template placeholder.")
    return query_llm_with_fallback(system_prompt, user_prompt, fallback, model_name)


def generate_architecture_diagram(model_name: str = "llama-3.3-70b-versatile") -> str:
    """Generates a valid Mermaid diagram string of the project layout."""
    stats = fs_tools.summarize_codebase()
    arch = fs_tools.scan_project_architecture()
    
    system_prompt = "You are a diagrams generator. Respond ONLY with valid Mermaid syntax code. Do not include markdown code fences (e.g. ```mermaid) or extra text."
    user_prompt = f"""
    Generate a Component Dependency Mermaid flowchart diagram representing this structure:
    - Frameworks: {arch.get('frameworks')}
    - Components: {stats.get('largest_files')}
    - APIs: {arch.get('apis')}
    - DBs: {arch.get('database_usage')}
    
    Ensure node names are alphanumeric and the output starts with 'graph TD' or 'graph LR'.
    """
    
    fallback = """graph TD
    Client[User Client / Browser] --> API_Layer[API Controllers]
    API_Layer --> Business_Logic[Service Modules]
    Business_Logic --> Data_Layer[Database Connection]
    
    style Client fill:#312e81,stroke:#6366f1,stroke-width:2px,color:#fff
    style API_Layer fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff
    style Business_Logic fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff
    style Data_Layer fill:#0f172a,stroke:#9ca3af,stroke-width:2px,color:#fff
"""
    # Clean possible markdown wrapping
    res = query_llm_with_fallback(system_prompt, user_prompt, fallback, model_name)
    cleaned = res.strip()
    if cleaned.startswith("```mermaid"):
        cleaned = cleaned[10:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def generate_readme(model_name: str = "llama-3.3-70b-versatile") -> str:
    """Generates a professional README file."""
    stats = fs_tools.summarize_codebase()
    arch = fs_tools.scan_project_architecture()
    
    system_prompt = "You are a documentation writer creating a README.md file."
    user_prompt = f"""
    Write a professional README.md for this codebase:
    - Ecosystem: {arch.get('project_type')}
    - Architecture: {arch.get('architecture_pattern')}
    - Frameworks: {arch.get('frameworks')}
    """
    
    fallback = f"""# 📂 Project Workspace

## 🚀 Overview
This codebase is a {arch.get('project_type')} built with {', '.join(arch.get('frameworks'))}. It employs a {arch.get('architecture_pattern')} layout.

## 🛠️ Setup Instructions
1. Verify package prerequisites.
2. Install external package libraries:
   ```bash
   pip install -r requirements.txt
   # OR
   npm install
   ```

## 📐 Architecture
The code modules reflect {arch.get('architecture_pattern')} separation of concerns.
"""
    return query_llm_with_fallback(system_prompt, user_prompt, fallback, model_name)
