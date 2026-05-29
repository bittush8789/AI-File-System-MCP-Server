import streamlit as st
import requests
import os
import json
import pandas as pd
import plotly.express as px
from pathlib import Path
from dotenv import load_dotenv
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components

# Load environment variables
load_dotenv("d:/File-system/.env")

BACKEND_URL = "http://127.0.0.1:8000"

# Page configuration
st.set_page_config(
    page_title="AI File System MCP Portal",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphism Dark Theme
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* Global Font & Background overrides */
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}
code, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Background gradient styling */
.stApp {
    background: radial-gradient(circle at top right, #1e1b4b, #0f0f16, #020205);
    color: #e2e8f0;
}

/* Glassmorphism Cards */
.glass-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(16px);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    transition: all 0.3s ease-in-out;
}
.glass-card:hover {
    transform: translateY(-2px);
    border-color: rgba(99, 102, 241, 0.3);
    box-shadow: 0 12px 40px 0 rgba(99, 102, 241, 0.15);
}

/* Premium Title Gradients */
.gradient-title {
    background: linear-gradient(135deg, #a5b4fc 0%, #818cf8 50%, #6366f1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}
.gradient-subtitle {
    color: #94a3b8;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}

/* Custom Metric Styling */
.custom-metric {
    text-align: center;
}
.custom-metric-value {
    font-size: 2.75rem;
    font-weight: 800;
    background: linear-gradient(135deg, #f43f5e, #fb7185);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.custom-metric-label {
    font-size: 0.95rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
}

/* Clean Custom Buttons */
.stButton>button {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.6rem 1.8rem;
    font-weight: 600;
    transition: all 0.2s ease;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
}
.stButton>button:hover {
    transform: scale(1.02);
    box-shadow: 0 6px 22px rgba(99, 102, 241, 0.5);
    background: linear-gradient(135deg, #818cf8 0%, #6366f1 100%);
}

/* File Tree Explorer nodes */
.folder-node {
    color: #38bdf8;
    font-weight: 600;
    cursor: pointer;
}
.file-node {
    color: #cbd5e1;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

# Helper function to render Mermaid diagrams safely
def render_mermaid(mermaid_code: str):
    html_code = f"""
    <div class="mermaid" style="background-color: transparent; display: flex; justify-content: center; align-items: center;">
    {mermaid_code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'dark', securityLevel: 'loose' }});
    </script>
    """
    components.html(html_code, height=500, scrolling=True)

# Sidebar Options Config
with st.sidebar:
    st.image("https://img.icons8.com/nolan/128/artificial-intelligence.png", width=65)
    st.markdown("## AI Code Workspace")
    st.markdown("---")
    
    selected_page = option_menu(
        menu_title=None,
        options=["Dashboard", "Upload", "Explorer", "Documentation", "Architecture", "Security", "Chat"],
        icons=["speedometer2", "cloud-upload", "folder2-open", "file-earmark-text", "diagram-3", "shield-lock", "chat-square-dots"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#818cf8", "font-size": "1.1rem"}, 
            "nav-link": {"font-size": "1rem", "text-align": "left", "margin":"0px", "color":"#94a3b8", "transition": "all 0.2s"},
            "nav-link-selected": {"background-color": "rgba(99, 102, 241, 0.15)", "color": "#e2e8f0", "border-left": "4px solid #6366f1"},
        }
    )
    
    st.markdown("---")
    st.sidebar.subheader("⚙️ Settings")
    groq_key = st.sidebar.text_input("Groq API Key", value=os.getenv("GROQ_API_KEY", ""), type="password")
    if st.sidebar.button("💾 Save Settings"):
        env_path = Path("d:/File-system/.env")
        with open(env_path, "w") as f:
            f.write(f"GROQ_API_KEY={groq_key}\n")
        os.environ["GROQ_API_KEY"] = groq_key
        st.sidebar.success("Updated settings!")

# Sidebar health check connection
backend_ok = False
try:
    health_resp = requests.get(f"{BACKEND_URL}/health", timeout=2).json()
    backend_ok = True
except Exception:
    pass

if not backend_ok:
    st.sidebar.markdown("🔴 **Backend Status:** Offline")
else:
    st.sidebar.markdown(f"🟢 **Backend Status:** Connected")

# Load analysis information globally to optimize loading times
analysis_data = None
if backend_ok:
    try:
        res = requests.post(f"{BACKEND_URL}/analyze-project", timeout=6)
        if res.status_code == 200:
            analysis_data = res.json()
    except Exception:
        pass


# ---------------- PAGE ROUTING ----------------

if selected_page == "Dashboard":
    st.markdown("<div class='gradient-title'>📈 Project Intelligence Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='gradient-subtitle'>Static & AI analysis of your repository workspace</div>", unsafe_allow_html=True)
    
    if not analysis_data or not analysis_data.get("stats", {}).get("total_files"):
        st.info("👋 Welcome! Go to the **Upload** page to load a project folder ZIP file to begin analysis.")
    else:
        stats = analysis_data.get("stats", {})
        arch = analysis_data.get("architecture", {})
        summary = analysis_data.get("summary", "")
        
        # 1. Key Statistics row
        col1, col2, col3, col4, col5 = st.columns(5)
        metrics = [
            ("Files", stats.get("total_files", 0), col1),
            ("Folders", stats.get("total_folders", 0), col2),
            ("Classes", stats.get("total_classes", 0), col3),
            ("Functions", stats.get("total_functions", 0), col4),
            ("Ecosystem", arch.get("project_type", "Unknown"), col5)
        ]
        for label, val, col in metrics:
            with col:
                st.markdown(f"""
                <div class="glass-card custom-metric">
                    <div class="custom-metric-value">{val}</div>
                    <div class="custom-metric-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)
                
        # 2. Charts and Metadata
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("<div class='glass-card'><h3>📊 File Distribution</h3>", unsafe_allow_html=True)
            types = stats.get("file_types", {})
            if types:
                df = pd.DataFrame(list(types.items()), columns=["Type", "Count"])
                fig = px.pie(df, values="Count", names="Type", hole=0.4, color_discrete_sequence=px.colors.qualitative.G10)
                fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_chart2:
            st.markdown("<div class='glass-card'><h3>🐘 Codebase Distribution (Largest Files)</h3>", unsafe_allow_html=True)
            large_files = stats.get("largest_files", [])
            if large_files:
                df = pd.DataFrame(large_files)
                df["Size (KB)"] = (df["size"] / 1024).round(2)
                fig = px.bar(df, x="Size (KB)", y="path", orientation="h", color="Size (KB)", color_continuous_scale="Purples")
                fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        # 3. AI Codebase Summary
        st.markdown("<div class='glass-card'><h2>🧠 AI Codebase Summary</h2>", unsafe_allow_html=True)
        st.markdown(summary)
        st.markdown("</div>", unsafe_allow_html=True)


elif selected_page == "Upload":
    st.markdown("<div class='gradient-title'>📂 Project Folder Upload</div>", unsafe_allow_html=True)
    st.markdown("<div class='gradient-subtitle'>Upload a ZIP archive to analyze a repository</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class='glass-card'>
        <h3>📁 Upload Guide</h3>
        <p>1. Zip your project folder on your local machine.</p>
        <p>2. Drag & Drop the zip file below.</p>
        <p>3. The backend will extract it automatically, perform static inspection, and update the AI vector indexing index.</p>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Select project ZIP archive", type="zip")
    if uploaded_file is not None:
        if st.button("🚀 Upload & Analyze Codebase"):
            with st.spinner("Extracting ZIP contents and rebuilding workspace vector store..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/zip")}
                    res = requests.post(f"{BACKEND_URL}/upload-zip", files=files)
                    if res.status_code == 200:
                        st.success(res.json().get("message", "Project uploaded!"))
                        st.balloons()
                        # Force refresh analysis
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {res.text}")
                except Exception as e:
                    st.error(f"Error connecting to backend: {str(e)}")


elif selected_page == "Explorer":
    st.markdown("<div class='gradient-title'>🔍 File Tree Explorer</div>", unsafe_allow_html=True)
    st.markdown("<div class='gradient-subtitle'>Browse codebase items, preview contents and search structures</div>", unsafe_allow_html=True)
    
    # 1. Advanced Search Filters
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        search_query = st.text_input("🔍 Search files, classes, functions, routes or APIs", value="", placeholder="e.g. def authenticate, /users, Class User")
    with col_s2:
        search_type = st.selectbox("Search Target", ["Global Match", "Files Only", "API Routes"])
    
    if search_query:
        with st.spinner("Searching codebase..."):
            try:
                res = requests.post(f"{BACKEND_URL}/search-files", json={"query": search_query})
                if res.status_code == 200:
                    results = res.json().get("results", [])
                    if results:
                        st.success(f"Found {len(results)} matches:")
                        for r in results:
                            # Render match line and path details
                            line_str = f"Line {r.get('line')}: " if r.get("line") else ""
                            st.code(f"[{r.get('type')}] {r.get('path')}\n{line_str}{r.get('preview')}", language="python")
                    else:
                        st.info("No matching components or text matches found.")
            except Exception as e:
                st.error(str(e))
    st.markdown("</div>", unsafe_allow_html=True)
    
    # 2. Folder Navigation List & Inline File Reader
    col_tree, col_viewer = st.columns([1, 2])
    
    with col_tree:
        st.markdown("<div class='glass-card'><h3>📁 Files Directory</h3>", unsafe_allow_html=True)
        # Fetch current path list
        try:
            res = requests.get(f"{BACKEND_URL}/list-files?path=")
            if res.status_code == 200:
                file_tree = res.json()
                for item in file_tree:
                    icon = "📁" if item["is_dir"] else "📄"
                    label = f"{icon} {item['name']}"
                    
                    if st.button(label, key=f"tree_{item['path']}"):
                        st.session_state["selected_explore_file"] = item["path"]
            else:
                st.info("Workspace directory empty.")
        except Exception:
            st.error("Failed to list files from backend.")
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_viewer:
        st.markdown("<div class='glass-card'><h3>📄 File Viewer & Editor</h3>", unsafe_allow_html=True)
        selected_file = st.session_state.get("selected_explore_file")
        if selected_file:
            st.markdown(f"**Viewing:** `{selected_file}`")
            try:
                res = requests.post(f"{BACKEND_URL}/read-file", json={"path": selected_file})
                if res.status_code == 200:
                    file_content = res.json().get("content", "")
                    
                    # Edit area
                    edited_content = st.text_area("Edit code contents", value=file_content, height=350)
                    if st.button("💾 Save Changes"):
                        save_res = requests.post(f"{BACKEND_URL}/write-file", json={"path": selected_file, "content": edited_content})
                        if save_res.status_code == 200:
                            st.success("File saved and indexed successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to save changes.")
                else:
                    st.error("Could not read file details.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        else:
            st.info("Select a file from the directory tree to view or edit.")
        st.markdown("</div>", unsafe_allow_html=True)


elif selected_page == "Documentation":
    st.markdown("<div class='gradient-title'>📄 AI Generated Documentation</div>", unsafe_allow_html=True)
    st.markdown("<div class='gradient-subtitle'>View or download automatically generated technical manuals</div>", unsafe_allow_html=True)
    
    docs_tabs = ["Installation Guide", "Configuration Guide", "API Documentation", "Folder Structure Explanation", "Deployment Guide", "Troubleshooting Section"]
    selected_tab = st.selectbox("Select Document Type", docs_tabs)
    
    if st.button("✨ Generate / Refresh Document"):
        with st.spinner("AI is documenting the repository..."):
            try:
                res = requests.post(f"{BACKEND_URL}/generate-doc-type", json={"doc_type": selected_tab})
                if res.status_code == 200:
                    st.session_state[f"doc_{selected_tab}"] = res.json().get("document", "")
            except Exception as e:
                st.error(str(e))
                
    doc_content = st.session_state.get(f"doc_{selected_tab}")
    if doc_content:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown(doc_content)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Download link
        st.download_button(
            label=f"📥 Download {selected_tab} (Markdown)",
            data=doc_content,
            file_name=f"{selected_tab.lower().replace(' ', '_')}.md",
            mime="text/markdown"
        )
    else:
        st.info("Click the button above to generate documentation for this section.")


elif selected_page == "Architecture":
    st.markdown("<div class='gradient-title'>📐 Architecture Analysis</div>", unsafe_allow_html=True)
    st.markdown("<div class='gradient-subtitle'>Rendered module dependency models and components flow charts</div>", unsafe_allow_html=True)
    
    if st.button("📐 Generate / Refresh Architecture Diagram"):
        with st.spinner("Mapping component relationships and generating visual layout..."):
            try:
                res = requests.post(f"{BACKEND_URL}/architecture")
                if res.status_code == 200:
                    st.session_state["arch_diagram"] = res.json().get("diagram", "")
            except Exception as e:
                st.error(str(e))
                
    diagram_code = st.session_state.get("arch_diagram")
    if diagram_code:
        st.markdown("<div class='glass-card'><h3>🧩 Component Visual Flowchart</h3>", unsafe_allow_html=True)
        render_mermaid(diagram_code)
        st.markdown("</div>", unsafe_allow_html=True)
        
        with st.expander("Show raw Mermaid syntax"):
            st.code(diagram_code, language="mermaid")
    else:
        st.info("Click the button above to map component relationships.")


elif selected_page == "Security":
    st.markdown("<div class='gradient-title'>🛡️ Security & Vulnerability Scan</div>", unsafe_allow_html=True)
    st.markdown("<div class='gradient-subtitle'>Check for secrets leakage, unsafe configurations, and credentials errors</div>", unsafe_allow_html=True)
    
    if st.button("🛡️ Run Security Scan"):
        with st.spinner("Scanning codebase static configurations..."):
            try:
                res = requests.post(f"{BACKEND_URL}/security-scan")
                if res.status_code == 200:
                    st.session_state["security_findings"] = res.json().get("findings", [])
            except Exception as e:
                st.error(str(e))
                
    findings = st.session_state.get("security_findings")
    if findings is not None:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        if not findings:
            st.success("🟢 No severe secrets leakage or credentials issues detected in files.")
        else:
            st.error(f"🔴 Detected {len(findings)} potential security warnings:")
            for idx, f in enumerate(findings, 1):
                st.markdown(f"**{idx}. File:** `{f['file']}` (Line {f['line']})")
                st.warning(f"⚠️ **Issue:** {f['issue']}")
                st.code(f"Snippet: {f['snippet']}")
                st.markdown("---")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Recommendations Report generator
        report_text = f"# Codebase Security Scan Report\n\nGenerated Findings: {len(findings) if findings else 0} alerts.\n"
        if findings:
            for f in findings:
                report_text += f"\n- File: {f['file']}:{f['line']}\n  Vulnerability: {f['issue']}\n"
        
        st.download_button(
            label="📥 Download Security Report",
            data=report_text,
            file_name="codebase_security_report.md",
            mime="text/markdown"
        )
    else:
        st.info("Click the button above to run the security vulnerability scan.")


elif selected_page == "Chat":
    st.markdown("<div class='gradient-title'>💬 AI Assistant Chat</div>", unsafe_allow_html=True)
    st.markdown("<div class='gradient-subtitle'>Ask technical questions, locate modules, explain APIs, or refactor files</div>", unsafe_allow_html=True)
    
    # Session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
        
    for q, a in st.session_state["chat_history"]:
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant"):
            st.markdown(a)
            
    user_input = st.chat_input("Ask any question about the codebase...")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
            
        with st.spinner("Searching codebase and reasoning..."):
            try:
                res = requests.post(f"{BACKEND_URL}/chat", json={"question": user_input})
                if res.status_code == 200:
                    answer = res.json().get("response", "")
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                    st.session_state["chat_history"].append((user_input, answer))
                else:
                    st.error("Error communicating with AI Assistant.")
            except Exception as e:
                st.error(str(e))
