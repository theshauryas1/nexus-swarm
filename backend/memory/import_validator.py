"""
AST-based Import, Package, and API validator.
Used to statically detect hallucinated libraries, missing packages, and invalid API attributes.
"""

import ast
import importlib.util
import os
import sys
import logging
from typing import List, Dict, Set

logger = logging.getLogger(__name__)

# Core python standard library modules list for quick fallback check
STD_LIB_MODULES = {
    "abc", "argparse", "array", "ast", "asyncio", "atexit", "base64", "bisect", "builtins",
    "bz2", "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code", "codecs", "collections",
    "colorsys", "compileall", "configparser", "contextlib", "contextvars", "copy", "copyreg",
    "crypt", "csv", "ctypes", "datetime", "dbm", "decimal", "difflib", "dis", "distutils",
    "doctest", "email", "encodings", "ensurepip", "enum", "errno", "faulthandler", "filecmp",
    "fileinput", "fnmatch", "formatter", "fractions", "ftplib", "functools", "gc", "getopt",
    "getpass", "gettext", "glob", "grp", "gzip", "hashlib", "heapq", "hmac", "html", "http",
    "imaplib", "imghdr", "importlib", "inspect", "io", "ipaddress", "itertools", "json",
    "keyword", "lib2to3", "linecache", "locale", "logging", "lzma", "mailbox", "mailcap",
    "marshal", "math", "mimetypes", "mmap", "modulefinder", "multiprocessing", "netrc",
    "nis", "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev", "parser",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
    "poplib", "posix", "pprint", "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
    "pydoc", "queue", "quopri", "random", "re", "readline", "resource", "rlcompleter",
    "runpy", "sched", "select", "selectors", "shelve", "shutil", "signal", "site", "smtpd",
    "smtplib", "sndhdr", "socket", "socketserver", "spwd", "sqlite3", "ssl", "stat",
    "statistics", "string", "stringprep", "struct", "subprocess", "sunau", "symbol",
    "symtable", "sys", "sysconfig", "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile",
    "termios", "test", "textwrap", "threading", "time", "timeit", "tkinter", "token",
    "tokenize", "trace", "traceback", "tracemalloc", "tty", "types", "typing", "unicodedata",
    "unittest", "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
    "wsgiref", "xdg", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib"
}

def _resolve_module_path(workspace_dir: str, module_name: str) -> str | None:
    """Resolve a module name (e.g. 'models.user') to a file path in the workspace."""
    parts = module_name.split(".")
    # Try as a folder with __init__.py first, or direct python file
    base_path = os.path.join(workspace_dir, *parts)
    if os.path.isdir(base_path):
        init_file = os.path.join(base_path, "__init__.py")
        if os.path.exists(init_file):
            return init_file
    
    file_path = base_path + ".py"
    if os.path.exists(file_path):
        return file_path
    
    return None

def _get_defined_names_in_file(file_path: str) -> Set[str]:
    """Parse a file statically and extract all globally defined names (classes, functions, imports, variables)."""
    names = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=file_path)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
                    elif isinstance(target, ast.Tuple):
                        for el in target.elts:
                            if isinstance(el, ast.Name):
                                names.add(el.id)
            elif isinstance(node, ast.Import):
                for name_node in node.names:
                    names.add(name_node.asname or name_node.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for name_node in node.names:
                    names.add(name_node.asname or name_node.name)
    except Exception as e:
        logger.warning(f"Error parsing local file {file_path} for defined names: {e}")
    return names

def validate_generated_imports(code_str: str, workspace_dir: str | None = None) -> List[Dict]:
    """
    Statically analyzes code_str to check that all imported modules and attributes exist.
    
    Returns:
        List of dicts, each with keys:
            - 'type': 'missing_import' | 'hallucinated_api'
            - 'module': module name
            - 'name': attribute name (if applicable)
            - 'reason': human-readable description
    """
    findings = []
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        # Code doesn't compile; let standard QA pytest runner catch syntax errors.
        # But we record it as a missing check.
        return [{"type": "syntax_error", "reason": f"Syntax error: {e}", "module": "", "name": ""}]

    # Collect standard library and third party modules to temporarily check dynamically
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name_node in node.names:
                full_name = name_node.name
                # Check top-level package name
                top_level = full_name.split(".")[0]
                
                # Check if it is a local module in workspace
                is_local = False
                if workspace_dir:
                    resolved = _resolve_module_path(workspace_dir, full_name)
                    if not resolved:
                        resolved = _resolve_module_path(workspace_dir, top_level)
                    if resolved:
                        is_local = True
                
                if is_local:
                    continue

                if top_level in STD_LIB_MODULES:
                    continue

                # Use find_spec to verify third party packages without loading them
                try:
                    spec = importlib.util.find_spec(top_level)
                    if spec is None:
                        findings.append({
                            "type": "missing_import",
                            "module": full_name,
                            "name": "",
                            "reason": f"Module '{full_name}' is not installed in the environment."
                        })
                except Exception as e:
                    findings.append({
                        "type": "missing_import",
                        "module": full_name,
                        "name": "",
                        "reason": f"Failed to inspect module '{full_name}': {e}"
                    })

        elif isinstance(node, ast.ImportFrom):
            module_name = node.module
            level = node.level

            # If it's a relative import, e.g. from .models import User
            if level > 0:
                if not workspace_dir:
                    continue # Cannot check relative import without workspace_dir
                # Find matching file relative to workspace
                # For simplified evaluation, we check workspace level directly
                resolved = _resolve_module_path(workspace_dir, module_name or "")
                if not resolved:
                    findings.append({
                        "type": "missing_import",
                        "module": module_name or f"level_{level}",
                        "name": "",
                        "reason": f"Relative module '{module_name}' could not be resolved in the workspace."
                    })
                    continue

                defined_names = _get_defined_names_in_file(resolved)
                for name_node in node.names:
                    imported_name = name_node.name
                    if imported_name == "*":
                        continue
                    if imported_name not in defined_names:
                        findings.append({
                            "type": "hallucinated_api",
                            "module": module_name,
                            "name": imported_name,
                            "reason": f"Name '{imported_name}' is not defined in local module '{module_name}'."
                        })
                continue

            # Absolute ImportFrom, e.g. from fastapi.security import JWTAuth
            if not module_name:
                continue

            top_level = module_name.split(".")[0]

            # 1. Check if it is local
            is_local = False
            if workspace_dir:
                resolved = _resolve_module_path(workspace_dir, module_name)
                if not resolved:
                    resolved = _resolve_module_path(workspace_dir, top_level)
                if resolved:
                    is_local = True

            if is_local:
                # Resolve attributes from local file statically
                resolved_file = _resolve_module_path(workspace_dir, module_name)
                if resolved_file:
                    defined_names = _get_defined_names_in_file(resolved_file)
                    for name_node in node.names:
                        imported_name = name_node.name
                        if imported_name == "*":
                            continue
                        if imported_name not in defined_names:
                            findings.append({
                                "type": "hallucinated_api",
                                "module": module_name,
                                "name": imported_name,
                                "reason": f"Name '{imported_name}' is not defined in local module '{module_name}'."
                            })
                else:
                    findings.append({
                        "type": "missing_import",
                        "module": module_name,
                        "name": "",
                        "reason": f"Module '{module_name}' could not be found in the workspace."
                    })
                continue

            # 2. Check standard library or third-party
            if top_level in STD_LIB_MODULES or importlib.util.find_spec(top_level) is not None:
                # Try importing to verify sub-modules or attributes dynamically in a sandbox
                try:
                    # Temporarily insert workspace_dir into sys.path to allow any internal imports to succeed
                    old_path = sys.path.copy()
                    if workspace_dir:
                        sys.path.insert(0, workspace_dir)
                    
                    try:
                        # Attempt to load the module
                        mod = importlib.import_module(module_name)
                        for name_node in node.names:
                            imported_name = name_node.name
                            if imported_name == "*":
                                continue
                            if not hasattr(mod, imported_name):
                                # Check if it is a submodule rather than an attribute, e.g., from fastapi.security import oauth2
                                sub_mod_name = f"{module_name}.{imported_name}"
                                try:
                                    importlib.import_module(sub_mod_name)
                                except Exception:
                                    findings.append({
                                        "type": "hallucinated_api",
                                        "module": module_name,
                                        "name": imported_name,
                                        "reason": f"Attribute or submodule '{imported_name}' not found in module '{module_name}'."
                                    })
                    finally:
                        sys.path = old_path
                except Exception as e:
                    findings.append({
                        "type": "missing_import",
                        "module": module_name,
                        "name": "",
                        "reason": f"Failed to import/verify module '{module_name}': {e}"
                    })
            else:
                findings.append({
                    "type": "missing_import",
                    "module": module_name,
                    "name": "",
                    "reason": f"Module '{module_name}' is not installed and not found locally."
                })

    return findings
