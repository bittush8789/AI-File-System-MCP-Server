import os
import logging
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv("d:/File-system/.env")

from backend.tools import fs_tools
from backend.vectorstore.vector_store import vector_store
from backend.services import ai_services
from backend.database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI File System MCP Server API Backend",
    description="Backend API exposing security-sandboxed filesystem operations, ChromaDB vector indexing, and AI Chat Assistant workflows.",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to index the codebase
@app.on_event("startup")
def startup_event():
    logger.info("Initializing Workspace index...")
    try:
        vector_store.index_all_workspace()
        logger.info("Workspace index completed successfully.")
    except Exception as e:
        logger.error(f"Error during workspace startup indexing: {str(e)}")

# Pydantic Schemas
class PathPayload(BaseModel):
    path: str = Field(..., description="Workspace relative or absolute path")

class WriteFilePayload(BaseModel):
    path: str = Field(..., description="Workspace file path")
    content: str = Field(..., description="File text contents")

class RenamePayload(BaseModel):
    old_path: str = Field(..., description="Source path")
    new_path: str = Field(..., description="Target path")

class QueryPayload(BaseModel):
    query: str = Field(..., description="Search query string")

class SemanticSearchPayload(BaseModel):
    query: str = Field(..., description="Semantic search query")
    limit: Optional[int] = Field(5, description="Maximum results to return")

class ChatPayload(BaseModel):
    question: str = Field(..., description="Question for the repository assistant")
    model_name: Optional[str] = Field("llama-3.3-70b-versatile", description="Groq model name to use")

class ScaffoldPayload(BaseModel):
    prompt: str = Field(..., description="Scaffold template request")
    model_name: Optional[str] = Field("llama-3.3-70b-versatile", description="Groq model name to use")

# Endpoints
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "workspace": str(fs_tools.WORKSPACE_DIR),
        "db_connected": True,
        "groq_available": os.getenv("GROQ_API_KEY") is not None
    }

@app.get("/list-files")
def list_files(path: str = ""):
    try:
        return fs_tools.list_workspace(path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/read-file")
def read_file_endpoint(payload: PathPayload):
    try:
        content = fs_tools.read_file(payload.path)
        return {"path": payload.path, "content": content}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/write-file")
def write_file_endpoint(payload: WriteFilePayload):
    try:
        msg = fs_tools.write_file(payload.path, payload.content)
        # Proactively update vector index for the modified file
        vector_store.index_file(payload.path)
        return {"status": "success", "message": msg}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-folder")
def create_folder_endpoint(payload: PathPayload):
    try:
        msg = fs_tools.create_folder(payload.path)
        return {"status": "success", "message": msg}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete-path")
def delete_path_endpoint(payload: PathPayload):
    try:
        # Delete from ChromaDB vector index
        rel_path = payload.path.replace('\\', '/')
        vector_store.delete_file_indices(rel_path)
        
        msg = fs_tools.delete_path(payload.path)
        return {"status": "success", "message": msg}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rename-path")
def rename_path_endpoint(payload: RenamePayload):
    try:
        msg = fs_tools.rename_path(payload.old_path, payload.new_path)
        # Update vector index
        vector_store.index_file(payload.new_path)
        return {"status": "success", "message": msg}
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-files")
def search_files_endpoint(payload: QueryPayload):
    try:
        results = fs_tools.search_files(payload.query)
        return {"query": payload.query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize-codebase")
def summarize_codebase_endpoint():
    try:
        return fs_tools.summarize_codebase()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-docs")
def generate_docs_endpoint():
    try:
        result = fs_tools.generate_docs()
        # Index newly created documents
        for filename, rel_path in result.items():
            vector_store.index_file(rel_path)
        return {"status": "success", "files": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/semantic-search")
def semantic_search_endpoint(payload: SemanticSearchPayload):
    try:
        results = vector_store.semantic_search(payload.query, payload.limit)
        return {"query": payload.query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat_endpoint(payload: ChatPayload):
    try:
        response = ai_services.chat_assistant(payload.question, payload.model_name)
        return {"question": payload.question, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analytics")
def analytics_endpoint():
    try:
        codebase_stats = fs_tools.summarize_codebase()
        repo_intelligence = ai_services.analyze_repository()
        
        # Pull history stats
        chat_hist = db.get_chat_history()
        search_hist = db.get_search_history()
        
        return {
            "stats": codebase_stats,
            "intelligence": repo_intelligence,
            "chat_history_count": len(chat_hist),
            "search_history_count": len(search_hist)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/project-scaffold")
def project_scaffold_endpoint(payload: ScaffoldPayload):
    try:
        msg = ai_services.auto_project_generator(payload.prompt, payload.model_name)
        # Update vector db
        vector_store.index_all_workspace()
        return {"status": "success", "message": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DocRequestPayload(BaseModel):
    doc_type: str = Field(..., description="Type of document to generate")
    model_name: Optional[str] = Field("llama-3.3-70b-versatile", description="Model name to use")


@app.post("/upload-zip")
async def upload_zip_endpoint(file: UploadFile = File(...)):
    try:
        # Save temporary zip file content
        import io
        zip_bytes = await file.read()
        extracted_count = fs_tools.extract_zip_to_workspace(io.BytesIO(zip_bytes))
        
        # Trigger codebase re-indexing
        vector_store.index_all_workspace()
        
        return {
            "status": "success",
            "message": f"Successfully uploaded and extracted {extracted_count} files to the workspace sandbox.",
            "extracted_count": extracted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-project")
def analyze_project_endpoint(payload: Optional[ChatPayload] = None):
    model = payload.model_name if payload else "llama-3.3-70b-versatile"
    try:
        stats = fs_tools.summarize_codebase()
        arch = fs_tools.scan_project_architecture()
        ai_summary = ai_services.generate_project_summary(model)
        return {
            "stats": stats,
            "architecture": arch,
            "summary": ai_summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-readme")
def generate_readme_endpoint(payload: Optional[ChatPayload] = None):
    model = payload.model_name if payload else "llama-3.3-70b-versatile"
    try:
        readme_content = ai_services.generate_readme(model)
        return {"readme": readme_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/security-scan")
def security_scan_endpoint():
    try:
        findings = fs_tools.scan_security()
        return {"findings": findings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dependency-analysis")
def dependency_analysis_endpoint():
    try:
        analysis = fs_tools.analyze_dependencies()
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/architecture")
def architecture_endpoint(payload: Optional[ChatPayload] = None):
    model = payload.model_name if payload else "llama-3.3-70b-versatile"
    try:
        diagram = ai_services.generate_architecture_diagram(model)
        return {"diagram": diagram}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-doc-type")
def generate_doc_type_endpoint(payload: DocRequestPayload):
    try:
        doc = ai_services.generate_codebase_docs(payload.doc_type, payload.model_name)
        return {"document": doc}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
