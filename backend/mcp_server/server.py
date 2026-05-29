import json
from mcp.server.fastmcp import FastMCP
from backend.tools import fs_tools

mcp_server = FastMCP("ai-filesystem-mcp")

@mcp_server.tool()
def read_file(path: str) -> str:
    """
    Read the content of a file within the workspace.
    
    Args:
        path (str): The relative or absolute path of the file to read.
    """
    try:
        return fs_tools.read_file(path)
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp_server.tool()
def write_file(path: str, content: str) -> str:
    """
    Write content to a file in the workspace.
    
    Args:
        path (str): The relative or absolute path of the file.
        content (str): The content to write.
    """
    try:
        return fs_tools.write_file(path, content)
    except Exception as e:
        return f"Error writing file: {str(e)}"

@mcp_server.tool()
def create_folder(path: str) -> str:
    """
    Create a folder inside the workspace.
    
    Args:
        path (str): The relative or absolute path of the folder to create.
    """
    try:
        return fs_tools.create_folder(path)
    except Exception as e:
        return f"Error creating folder: {str(e)}"

@mcp_server.tool()
def search_files(query: str) -> str:
    """
    Search workspace files matching query in name or contents.
    
    Args:
        query (str): The text or filename pattern to search for.
    """
    try:
        results = fs_tools.search_files(query)
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching files: {str(e)}"

@mcp_server.tool()
def summarize_codebase() -> str:
    """
    Summarize the workspace codebase structure and collect metrics.
    """
    try:
        results = fs_tools.summarize_codebase()
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error summarizing codebase: {str(e)}"

@mcp_server.tool()
def generate_docs() -> str:
    """
    Automatically generate documentation files (README, API_DOCS, ARCHITECTURE) in workspace.
    """
    try:
        results = fs_tools.generate_docs()
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error generating docs: {str(e)}"
