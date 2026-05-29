import pytest
import io
import zipfile
from pathlib import Path
from backend.tools import fs_tools
from backend.utils.security import WORKSPACE_DIR

def test_zip_extraction_sandbox():
    # Create a mock zip in-memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as z:
        z.writestr("test_extract.py", "print('hello extraction')")
        z.writestr("subdir/sub.js", "console.log('subdir')")
        # Try path traversal
        z.writestr("../outside.txt", "traversal attempt")
        
    zip_buffer.seek(0)
    count = fs_tools.extract_zip_to_workspace(zip_buffer)
    assert count == 2 # traversal skipped
    
    assert (WORKSPACE_DIR / "test_extract.py").exists()
    assert (WORKSPACE_DIR / "subdir/sub.js").exists()
    assert not (WORKSPACE_DIR.parent / "outside.txt").exists()


def test_dependency_parsing():
    # Write sample dependency file
    fs_tools.write_file("requirements.txt", "requests==2.28.1\nflask>=2.0.0\n# comment\n")
    
    analysis = fs_tools.analyze_dependencies()
    packages = [d["name"] for d in analysis["list"]]
    assert "requests" in packages
    assert "flask" in packages


def test_security_scanner():
    # Write sensitive credentials file
    fs_tools.write_file("secrets.env", "AWS_SECRET_KEY = \"aws_secret_access_key='abc123xyz456efg789012345efg7890123456789'\"\n")
    
    findings = fs_tools.scan_security()
    assert len(findings) >= 1
    assert any("AWS" in f["issue"] for f in findings)


def test_architecture_scanner():
    fs_tools.write_file("routes.py", "@app.get('/users/profile')\ndef profile(): pass\n")
    
    arch = fs_tools.scan_project_architecture()
    apis = [a["path"] for a in arch["apis"]]
    assert "/users/profile" in apis
