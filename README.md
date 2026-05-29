# AI File System Model Context Protocol (MCP) Server & Console Portal

An enterprise-grade, secure, and intuitive Developer Assistant and codebase analysis portal. The application integrates a custom **MCP Server** built with the FastMCP SDK, a **FastAPI backend** managing database state and similarity vector indexing, and a premium **Streamlit dashboard interface**.

---

## 📖 Project Overview

### The Problem
Modern software development involves managing rapidly growing, complex codebases. Developers frequently spend up to 70% of their time reading code, tracking architecture diagrams, validating security issues, and searching for dependencies rather than writing code. Existing solutions are either fully cloud-bound (presenting compliance and intellectual property risks) or lack the interactive local capabilities to inspect, search, and edit files securely within sandboxed boundaries.

### The Purpose
The **AI File System MCP Server & Console Portal** is built to bridge this gap. It provides a secure local environment that allows developers to:
1. Upload complete repository packages as ZIP archives.
2. Index files into a local vector DB (ChromaDB) for semantic code search.
3. Automatically perform dependency mappings, security scanning (secrets/keys leak detection), and code quality checks.
4. Interface with agents or humans using standard Model Context Protocol (MCP) tool bindings.

### Target Users
- **Software Engineers & Technical Leads**: For rapid onboarding to new or unfamiliar codebases.
- **Security & Compliance Auditors**: For scanning packages for hardcoded credentials, credentials leakage, and environment issues.
- **AI Agents**: Utilizing the codebase as an MCP Server to locate functions, modify scripts, and generate documents.

### Key Business Value
- **100% Data Sovereignty**: All analysis, vector stores, and processing occur locally.
- **Fast Developer Onboarding**: Generates onboarding documentation, architecture charts, and modular summaries instantly.
- **Risk Mitigation**: Flags severe secrets (e.g. AWS Keys, database credentials) before committing to remote version control systems.

---

## ⚡ Features

### 1. Folder Upload & Sandboxing
- **Secure Archive Extraction**: Upload projects in standard ZIP format. The system automatically extracts, inventories, and verifies paths inside a sandboxed workspace directory.
- **Directory Confining**: The backend utilizes strict folder boundaries, throwing `PermissionError` on any directory traversal attempts (e.g. `../../` or absolute path breakouts).

### 2. Static Ecosystem & Dependency Scanning
- **Dependency Parser**: Parses files like `requirements.txt` and `package.json` to extract libraries, detect outdated versions, and find unused packages.
- **Architecture Scaffolding**: Automatically detects programming languages, database connectors, and active frameworks (e.g., FastAPI, Express, React, Flask).

### 3. Automated Code Quality & Security Audits
- **Key & Secrets Scanner**: Identifies AWS secret keys, database URIs, Slack tokens, Gemini/OpenAI API keys, and database passwords.
- **Quality Indicators**: Detects large functions (exceeding 50 lines), dead function definitions, code duplications, and maintainability concerns.

### 4. Interactive Documentation & Architecture Viewer
- **AI Technical Writing**: Automatically drafts installation guides, API descriptions, troubleshooting steps, and configurations.
- **Mermaid Graph Render**: Translates component relationships and database linkages into interactive Mermaid flowchart diagrams.

### 5. Semantic Code Search & RAG Chat
- **Vector Search Engine**: Indexes codebase splits into ChromaDB for similarity searching using local mock embeddings or OpenAI/Gemini vectors.
- **AI Assistant Chat**: Integrates with Groq, OpenAI, or Gemini for context-aware Q&A based on workspace code fragments.

---

## 🎯 Use Cases

- **Codebase Auditing & Security Scans**: Upload code repositories to verify that no passwords or development API keys are left in environment files.
- **Scaffolding Verification**: Test structure schemas, check dead code definitions, and identify bloated code modules.
- **RAG-Based Technical Support**: Run queries like `"Explain how authentication is structured in this repository"` and get answers pointing to exact lines of code.

---

## 📐 System Architecture

### HLD System Overview
The portal employs a clean, decoupled architecture:
1. **Frontend View Layer (Streamlit)**: Serves as the user portal. Communicates via REST APIs with the backend.
2. **Backend API Layer (FastAPI)**: Coordinates endpoints, file validations, SQLite data entries, and triggers ChromaDB vector indexing.
3. **Storage & Embedding Layer**:
   - **SQLite**: Persists search history, chat logs, and workspace file registers.
   - **ChromaDB**: Persists vector representations of codebase splits.
   - **Workspace Sandbox**: A directory confined physically on the disk.

### Component Responsibilities
- **`fs_tools`**: Conducts safe extraction, file validation, security audits, and dependency parsing.
- **`ai_services`**: Designs prompt schemas, connects to LLMs, and yields READMEs, manuals, and Mermaid scripts.
- **`vector_store`**: Processes document splits, updates database contents, and performs similarity searches.

### Data Flow
Information flows from the client upload through the security sandboxing modules before being persisted in the workspace filesystem. Staged text triggers incremental vector encoding into ChromaDB and metadata registry into the SQLite tables.

### Request Flow
Requests are dispatched from the Streamlit single-page application, routing through local JSON payloads to the FastAPI API handlers. Sanitization occurs synchronously before calling core filesystem tools.

### Processing Flow
Operations undergo a linear pipeline: Parameter Sanitation -> Workspace Bounds Guarding -> Action Execution (Static Audit, AI Prompting, or File Mutation) -> Output Logging.

### User Interaction Flow
The user interacts via the sidebar menu tabs. The application responds asynchronously using spinners, dynamic Mermaid chart rendering, and exportable Markdown report files.

---

## 📊 Architecture Diagram

### High-Level Architecture
```mermaid
graph TD
    User([User Developer]) <--> Streamlit[Streamlit Portal]
    Streamlit <--> FastAPI[FastAPI Backend]
    FastAPI <--> SQLite[(SQLite Database)]
    FastAPI <--> Chroma[(ChromaDB Vector Store)]
    FastAPI <--> Workspace[(Workspace Sandbox Folder)]
    FastAPI <--> LLM[LLM API Services: Groq/OpenAI/Gemini]
```

### User Request Flow
```mermaid
sequenceDiagram
    actor User
    participant Frontend as Streamlit UI
    participant Backend as FastAPI Server
    participant Tools as File System Tools
    
    User->>Frontend: Upload ZIP File
    Frontend->>Backend: POST /upload-zip (binary)
    Backend->>Tools: extract_zip_to_workspace()
    Tools-->>Backend: Files Extracted (N files)
    Backend->>Backend: Trigger Async Vector Indexing
    Backend-->>Frontend: HTTP 200 (Success)
    Frontend-->>User: Refresh Dashboard & Show Stats
```

### Internal Processing Flow
```mermaid
graph LR
    Upload[ZIP Archive] --> Extract[Safe Extractor]
    Extract --> SQLiteRegister[Register Files in SQLite]
    Extract --> Splitter[Code Chunker & Tokenizer]
    Splitter --> Embedder[Embeddings Engine]
    Embedder --> ChromaDB[(ChromaDB Store)]
```

### Component Interaction Flow
```mermaid
graph TD
    main.py[main.py: Routes Handler] --> fs_tools[fs_tools: System Operations]
    main.py --> ai_services[ai_services: Prompt Engine]
    main.py --> vector_store[vector_store: Chromadb Manager]
    fs_tools --> db[db: SQLite Interface]
```

---

## ⚙️ Project Workflow

1. **Initialization**: The user configures environment parameters (e.g. API keys) in the settings sidebar or `.env` file.
2. **Upload**: The user uploads a compressed folder (ZIP format) via the UI.
3. **Extraction & Indexing**: The backend purges previous workspace folders, extracts the ZIP contents, and registers the workspace index.
4. **Scanning**: Static scanners inspect dependencies, route annotations, and credentials.
5. **Consumption**: The user browses files in the Explorer, initiates RAG chats, updates code lines, or exports generated documentation.

---

## 🎯 Functional Requirements

- **ZIP File Processing**: Must extract, validate, and index projects in under 10 seconds for standard folders.
- **Sandbox Security**: Must reject any read, write, edit, or delete action referencing directories outside the `workspace/` folder.
- **AI-Powered Code Help**: Must answer developer questions referencing specific files, classes, and helper methods.
- **Architecture Flowcharts**: Must generate valid diagrams compatible with Mermaid layout standards.
- **Documentation Exporting**: Must compile summaries, READMEs, and scans into markdown files for download.

---

## 🚀 Non-Functional Requirements

- **Scalability**: Decoupled APIs allow the backend to run on container orchestration platforms while serving multiple frontend UI portals.
- **Reliability**: Uses database isolation; if ChromaDB is unavailable or LLM keys are missing, the system falls back to static analyzers without crashing.
- **Performance**: Keeps memory usage low during file reviews through file chunking.
- **Security**: Strict path resolutions block directory traversal attacks. Secrets are masked before displaying.
- **Maintainability**: Follows modular Python coding standards and utilizes pytest for integration testing.
- **Availability**: High redundancy support across API nodes.
- **Extensibility**: Clean adapter pattern for plugging in alternative vector stores or compiler parsers.

---

## 📂 Folder Structure

```text
ai-filesystem-mcp/ (d:/File-system/)
├── backend/
│   ├── api/
│   ├── database/
│   │   ├── db.py            # SQLite database logic and history logs
│   │   └── metadata.db      # SQLite binary database
│   ├── mcp_server/
│   │   └── server.py        # FastMCP SDK Tool definitions
│   ├── services/
│   │   └── ai_services.py   # LLM prompt orchestration and fallback generation
│   ├── tools/
│   │   └── fs_tools.py      # Safe ZIP extraction, file tree navigation, and security auditing
│   ├── utils/
│   │   └── security.py      # Confined sandbox resolver
│   ├── vectorstore/
│   │   ├── vector_store.py  # ChromaDB indexing client
│   │   └── .chroma/         # ChromaDB persistence directory
│   └── main.py              # FastAPI app routing
│
├── frontend/
│   └── app.py               # Streamlit Multi-page Dashboard
│
├── workspace/               # Confined sandboxed directory for files
├── tests/
│   ├── test_backend.py      # Original Pytest suite
│   └── test_analysis.py     # Static scanning & analysis unit tests
├── requirements.txt         # Package dependencies file
└── README.md                # System documentation
```

---

## 🧱 Core Modules

### 1. `backend/tools/fs_tools.py`
- **Responsibilities**: ZIP archive handling, path traversals verification, credentials analysis, and regex parsing.
- **Inputs**: Archive file bytes, workspace file names, or string search terms.
- **Outputs**: File streams, arrays of security threats, or JSON summaries.
- **Dependencies**: `zipfile`, `os`, `re`, `shutil`, `backend/database/db.py`.

### 2. `backend/services/ai_services.py`
- **Responsibilities**: Connects to LLM endpoints, wraps system templates, and translates files into summaries or architectural Mermaid scripts.
- **Inputs**: Structured metadata lists, questions, or diagram prompts.
- **Outputs**: Markdown content strings, code snippets, or Mermaid definitions.
- **Dependencies**: `langchain`, `langchain-groq`, `langchain-openai`, `langchain-google-genai`.

### 3. `backend/vectorstore/vector_store.py`
- **Responsibilities**: Code chunking, document loading, similarity distance computation, and ChromaDB reads.
- **Inputs**: Text file splits or natural language queries.
- **Outputs**: Vector coordinates, match indices, and code chunk previews.
- **Dependencies**: `chromadb`, `langchain-text-splitters`.

---

## 🔒 Security Considerations

1. **Authentication**: Optional API key tokens for production API routes.
2. **Authorization**: Basic file operations are restricted to admin or local developers.
3. **Input Validation**: Path resolving checks for path traversals (e.g. `../`) and verifies execution boundaries.
4. **Secret Management**: Environmental variables are stored in local `.env` and excluded from git tracking.
5. **Secure File Handling**: Decompresses and extracts zip files with sanitization checks to prevent zip slip exploits.
6. **Access Control**: Role-based routing controls on core microservice levels.
7. **Security Best Practices**: Keeps workspace fully read-only unless explicit edits are triggered.

---

## ⚠️ Error Handling Strategy

- **Backend (FastAPI)**: Employs standard Exception handlers. Operation issues return HTTP 4xx (e.g. 403 Forbidden for traversal attempts, 404 for missing resources) and HTTP 500 for general failures.
- **Frontend (Streamlit)**: Catches connectivity drops and connection timeouts gracefully, switching panels to offline mode and warning users without crashing.

---

## 📝 Logging Strategy

- **Application Logs**: Standard Python `logging` streams core events (e.g., startup indexing, API requests) to standard output.
- **Audit Logs**: SQLite captures queries, searches, and generated documents.
- **Error Logs**: Captures and routes stack traces to std.error.
- **Monitoring Logs**: Heartbeats generated to monitor backend API uptime.

---

## 🗄️ Database Design

### SQLite Tables

#### `files`
| Column | Type | Description |
|---|---|---|
| `path` | TEXT (PK) | Workspace relative file path |
| `indexed_at` | TIMESTAMP | Entry registration date |

#### `chat_history`
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment key |
| `question` | TEXT | Prompt asked by user |
| `answer` | TEXT | Response generated |
| `timestamp` | TIMESTAMP | Time of conversation |

#### `search_history`
| Column | Type | Description |
|---|---|---|
| `id` | INTEGER (PK) | Auto-increment key |
| `query` | TEXT | Searched terms |
| `timestamp` | TIMESTAMP | Time of execution |

---

## 🧠 AI Processing Pipeline

1. **Input**: User initiates prompt.
2. **Context Enrichment**: ChromaDB executes a similarity search matching vector embeddings.
3. **Prompt Composition**: Combines matching fragments with system instructions.
4. **LLM Querying**: Sends payloads to Groq/OpenAI/Gemini.
5. **Answer Delivery**: Parses, formats, and displays answers.

---

## 📁 File Processing Pipeline

1. **Receive**: Binary zip stream accepted at `POST /upload-zip`.
2. **Clearance**: Current workspace contents are pruned safely.
3. **Extraction**: Safe loop extracts files individually, checking relative boundaries.
4. **Inventory**: SQLite registers paths for the file tree.

---

## 🔍 Analysis Pipeline

1. **Scouting**: Traverses files recursively in the workspace.
2. **Classification**: Collects files distribution counts by extension.
3. **Heuristics Mapping**: Flags functions with lines > 50 or those missing cross-module calls.

---

## 📄 Documentation Generation Pipeline

1. **Selection**: User specifies document template in UI.
2. **Aggregation**: System loads scanned structural ecosystems.
3. **Prompting**: AI models refine instructions into developer manuals.

---

## 🛡️ Security Scanning Pipeline

1. **Loading**: Reads files line-by-line using buffered loaders.
2. **Regex Auditing**: Evaluates patterns against known key identifiers.
3. **Reporting**: Assembles findings, masking secrets automatically.

---

## 🔧 Code Quality Analysis Pipeline

1. **Line Auditing**: Counts definitions and line counts.
2. **Unused Functions Scan**: Evaluates function invocations across codebase text.
3. **Refactoring Alerts**: Highlights long functions for decomposition.

---

## 📡 API Design

### 1. `POST /upload-zip`
- **Description**: Upload a ZIP archive to overwrite the workspace sandbox.
- **Request**: Multipart Form Data with a `file` field.
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Successfully uploaded and extracted 15 files to the workspace sandbox.",
    "extracted_count": 15
  }
  ```

### 2. `POST /analyze-project`
- **Description**: Get static metrics, architecture summaries, and high-level summaries.
- **Response (200 OK)**:
  ```json
  {
    "stats": {
      "total_files": 12,
      "total_folders": 3,
      "file_types": {".py": 10, ".txt": 2}
    },
    "architecture": {
      "project_type": "Python Ecosystem",
      "frameworks": ["FastAPI"],
      "architecture_pattern": "Standard layout"
    },
    "summary": "Project summary description..."
  }
  ```

### 3. `POST /security-scan`
- **Description**: Scan workspace files for credentials or vulnerable setups.
- **Response (200 OK)**:
  ```json
  {
    "findings": [
      {
        "file": "config.env",
        "line": 4,
        "issue": "Possible AWS Access Key ID detected",
        "severity": "High",
        "snippet": "AWS_KEY = AKIAIOSFODNN7EXAMPLE"
      }
    ]
  }
  ```

### 4. `POST /dependency-analysis`
- **Description**: Scan configuration parameters and packaging configurations.
- **Response (200 OK)**:
  ```json
  {
    "analysis": {
      "list": [{"name": "fastapi", "version": "0.100.0", "file": "requirements.txt"}],
      "outdated": [{"name": "fastapi", "current": "0.100.0", "latest": "3.9.0"}],
      "unused": []
    }
  }
  ```

---

## 📈 Scalability Considerations

- **State Externalization**: SQLite database and ChromaDB path descriptors can be migrated to external instances (e.g. Postgres and managed vector databases like Pinecone) to allow stateless API workers.
- **Caching**: Implements Redis caching for RAG queries to save computation costs.

---

## 🔮 Future Enhancements

- **AST Parsers**: Introduce robust AST validation to map comprehensive architecture graphs instead of string heuristics.
- **Multi-tenant Workspaces**: Enable virtual logical workspace folders per user.

---

## 📌 Assumptions

- **Sandbox Confined**: Workspace must reside inside path limits with valid write permissions.
- **Ecosystem**: Relies on standard packaging configurations (`requirements.txt`, `package.json`) to parse dependencies.

---

## 🚫 Limitations

- **Regex Boundaries**: Credentials scanning uses regex, which may yield false positives.
- **Local DB Scale**: SQLite and Chroma DB run locally, suitable for small to mid-sized codebases.

---

## 💻 Development Guidelines

- **Style Guide**: Follow PEP-8 rules for Python modules.
- **Modularity**: Implement logic under tools and keep API routers in `main.py` clean.

---

## 🧪 Testing Strategy

### Unit & Integration Testing
Run the comprehensive test suite to verify the application features:
```bash
.venv\Scripts\python -m pytest tests/
```
Tests cover:
- Confined workspace paths.
- Sandbox checks.
- File system APIs.
- ZIP extraction functionality.

---

## 🚀 Deployment Strategy

### Local Environment
For development or offline execution:
```bash
# Start Backend
.venv\Scripts\uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# Start Frontend Portal
.venv\Scripts\streamlit run frontend/app.py
```

### Production Setup (Docker)
Build and run the application in isolated containers:
```bash
docker-compose up --build
```
Access the application at `http://localhost:8501`.

---

## 📊 Monitoring and Observability

- **Metrics**: Standard prometheus metric bindings trace response codes and processing latencies.
- **Alerting**: System alerts triggered on failed container health checks or database failures.

---

## 🔍 Troubleshooting Guide

- **ChromaDB Issues**: Clean out `.chroma/` and rebuild indexes.
- **LLM Context Overflow**: Reduce file upload size or filter binary targets.

---

## ❓ FAQ

#### How is data kept private?
The application runs locally on your system. Unless you configure an external LLM API key, all data stays on your machine.

#### Does the vector search work offline?
Yes. The app falls back to standard text search and mock embeddings if no external AI API keys are configured, so you can still search the codebase offline.

#### How do traversal blocks behave?
The sandbox utility checks every path. If a path contains traversal segments (e.g. `../`) that resolve outside the workspace root, the operation is blocked and a `PermissionError` is raised.

---

## 🤝 Contributing Guidelines

We welcome contributions!
1. Fork this repository.
2. Create a branch for your feature (`git checkout -b feature/cool-idea`).
3. Verify your changes pass all unit tests (`python -m pytest tests/`).
4. Commit your changes and open a Pull Request.

---

## 📄 License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.
