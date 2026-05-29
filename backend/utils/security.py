import os
from pathlib import Path

WORKSPACE_DIR = Path("d:/File-system/workspace").resolve()

# Create workspace directory if it doesn't exist
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

def validate_path(path: str) -> Path:
    """
    Validates a file/folder path to ensure it is within the workspace directory.
    Prevents path traversal attacks.
    """
    # Resolve the path relative to the workspace directory
    requested_path = Path(path)
    
    # If the path is absolute, try to make it relative to the workspace if it's within it,
    # or reject it if it's completely outside the workspace.
    if requested_path.is_absolute():
        resolved_path = requested_path.resolve()
    else:
        resolved_path = (WORKSPACE_DIR / requested_path).resolve()
        
    # Check if the resolved path is within the workspace directory
    try:
        # relative_to throws ValueError if resolved_path is not under WORKSPACE_DIR
        resolved_path.relative_to(WORKSPACE_DIR)
    except ValueError:
        raise PermissionError(f"Access Denied: Path '{path}' is outside the workspace sandbox.")
        
    return resolved_path

def get_relative_path(absolute_path: Path) -> str:
    """
    Returns the relative path from the workspace root.
    """
    try:
        return str(absolute_path.relative_to(WORKSPACE_DIR)).replace('\\', '/')
    except ValueError:
        return str(absolute_path).replace('\\', '/')
