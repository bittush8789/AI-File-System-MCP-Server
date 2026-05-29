import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient

from backend.utils.security import validate_path, WORKSPACE_DIR
from backend.tools import fs_tools
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "workspace" in data

def test_path_validation_sandbox():
    # Safe path
    safe_path = validate_path("subfolder/file.py")
    assert safe_path.relative_to(WORKSPACE_DIR) is not None

    # Path traversal attack path outside workspace
    with pytest.raises(PermissionError):
        validate_path("../../outside.txt")

    with pytest.raises(PermissionError):
        validate_path("d:/File-system/../outside.txt")

def test_filesystem_operations():
    test_file = "test_run.py"
    test_content = "print('testing')"
    
    # Write file
    write_msg = fs_tools.write_file(test_file, test_content)
    assert "Successfully wrote" in write_msg
    assert (WORKSPACE_DIR / test_file).exists()
    
    # Read file
    read_content = fs_tools.read_file(test_file)
    assert read_content == test_content
    
    # Clean up file
    del_msg = fs_tools.delete_path(test_file)
    assert "Successfully deleted file" in del_msg
    assert not (WORKSPACE_DIR / test_file).exists()

def test_create_folder():
    test_dir = "test_directory"
    msg = fs_tools.create_folder(test_dir)
    assert "Successfully created directory" in msg
    assert (WORKSPACE_DIR / test_dir).is_dir()
    
    # Clean up folder
    fs_tools.delete_path(test_dir)
    assert not (WORKSPACE_DIR / test_dir).exists()
