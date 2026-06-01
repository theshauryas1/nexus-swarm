import os
import shutil
import tempfile
import pytest
from memory.import_validator import validate_generated_imports

def test_valid_standard_and_installed_imports():
    code = """
import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer
"""
    findings = validate_generated_imports(code)
    # Both os, sys, fastapi, and OAuth2PasswordBearer should be found and succeed.
    assert len(findings) == 0

def test_invalid_hallucinated_imports():
    code = """
import os
import nonexistent_module_xyz
from fastapi.security import JWTAuth
from sys import nonexistent_sys_function
"""
    findings = validate_generated_imports(code)
    assert len(findings) > 0
    
    types = [f["type"] for f in findings]
    modules = [f["module"] for f in findings]
    names = [f["name"] for f in findings]
    
    assert "missing_import" in types
    assert "nonexistent_module_xyz" in modules
    
    assert "hallucinated_api" in types
    assert "fastapi.security" in modules
    assert "JWTAuth" in names
    
    assert "sys" in modules
    assert "nonexistent_sys_function" in names

def test_local_workspace_imports():
    # Setup a mock workspace
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a local module in workspace: models.py
        models_content = """
class User:
    pass

def get_user():
    pass
"""
        with open(os.path.join(tmp_dir, "models.py"), "w", encoding="utf-8") as f:
            f.write(models_content)
            
        # Create nested package: utils/math.py
        os.makedirs(os.path.join(tmp_dir, "utils"), exist_ok=True)
        with open(os.path.join(tmp_dir, "utils", "__init__.py"), "w", encoding="utf-8") as f:
            f.write("")
        with open(os.path.join(tmp_dir, "utils", "math.py"), "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

        # Test valid local imports
        code_valid = """
from models import User, get_user
from utils.math import add
"""
        findings = validate_generated_imports(code_valid, workspace_dir=tmp_dir)
        assert len(findings) == 0
        
        # Test hallucinated local imports
        code_invalid = """
from models import User, NonexistentClass
from utils.math import subtract
import nonexistent_local_file
"""
        findings = validate_generated_imports(code_invalid, workspace_dir=tmp_dir)
        assert len(findings) == 3
        
        types = [f["type"] for f in findings]
        names = [f["name"] for f in findings]
        modules = [f["module"] for f in findings]
        
        assert "hallucinated_api" in types
        assert "NonexistentClass" in names
        assert "subtract" in names
        assert "nonexistent_local_file" in modules
