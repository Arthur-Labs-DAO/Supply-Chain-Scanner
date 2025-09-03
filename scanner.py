#!/usr/bin/env python3
"""
Blockchain Supply Chain
Import this into your SCM / ERP tool to deploy specific smart contracts
"""

import os
import ast
from pathlib import Path
from flask import Flask, jsonify, request
import socket
from contextlib import closing
import subprocess
import json
import re

# --- Mock Encryption System ---
def basic_encrypt(data):
    """A simple XOR cipher for demonstration purposes."""
    key = 42
    return ''.join(chr(ord(c) ^ key) for c in data)

def basic_decrypt(data):
    """Decrypts data encrypted with basic_encrypt."""
    key = 42
    return ''.join(chr(ord(c) ^ key) for c in data)

# --- Python Project Scanner (Original Code, unchanged) ---

def find_free_port(start_port=8003):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        for port in range(start_port, start_port + 100):
            try:
                s.bind(('localhost', port))
                return port
            except OSError:
                continue
        raise OSError("No free ports found")

class PythonProjectScanner:
    def __init__(self, project_path=None):
        if project_path is None:
            current = Path.cwd()
            project_indicators = [
                'setup.py', 'pyproject.toml', 'requirements.txt',
                'Pipfile', 'poetry.lock', 'environment.yml',
                '.git', 'src', 'lib', 'app', 'apps'
            ]
            if any((current / indicator).exists() for indicator in project_indicators):
                self.project_path = current
            else:
                for parent in current.parents:
                    if any((parent / indicator).exists() for indicator in project_indicators):
                        self.project_path = parent
                        break
                else:
                    self.project_path = current
        else:
            self.project_path = Path(project_path)
        print(f"Scanning Python project at: {self.project_path}")

    def analyze_function(self, func_node):
        args = []
        for arg in func_node.args.args:
            arg_info = {'name': arg.arg, 'type': None}
            if arg.annotation:
                try:
                    arg_info['type'] = ast.unparse(arg.annotation)
                except:
                    arg_info['type'] = 'unknown'
            args.append(arg_info)
        if func_node.args.vararg:
            args.append({
                'name': f"*{func_node.args.vararg.arg}",
                'type': 'varargs'
            })
        if func_node.args.kwarg:
            args.append({
                'name': f"**{func_node.args.kwarg.arg}",
                'type': 'kwargs'
            })
        return_type = None
        if func_node.returns:
            try:
                return_type = ast.unparse(func_node.returns)
            except:
                return_type = 'unknown'
        decorators = []
        for decorator in func_node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except:
                decorators.append('decorator')
        return {
            'name': func_node.name,
            'line': func_node.lineno,
            'args': args,
            'return_type': return_type,
            'decorators': decorators,
            'docstring': ast.get_docstring(func_node) or 'No documentation',
            'is_async': isinstance(func_node, ast.AsyncFunctionDef)
        }

    def analyze_class(self, class_node):
        methods = []
        attributes = []
        for child in class_node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self.analyze_function(child))
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        try:
                            value = ast.unparse(child.value)
                        except:
                            value = 'complex_value'
                        attributes.append({
                            'name': target.id,
                            'value': value,
                            'line': child.lineno
                        })
        bases = []
        for base in class_node.bases:
            try:
                bases.append(ast.unparse(base))
            except:
                bases.append('unknown_base')
        return {
            'name': class_node.name,
            'line': class_node.lineno,
            'methods': methods,
            'attributes': attributes,
            'bases': bases,
            'docstring': ast.get_docstring(class_node) or 'No documentation'
        }

    def analyze_constants(self, tree):
        constants = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        try:
                            value = ast.unparse(node.value)
                        except:
                            value = 'complex_value'
                        constants.append({
                            'name': target.id,
                            'value': value,
                            'line': node.lineno
                        })
        return constants

    def analyze_imports(self, tree):
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'module': alias.name,
                        'alias': alias.asname,
                        'type': 'import'
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append({
                        'module': f"{module}.{alias.name}" if module else alias.name,
                        'alias': alias.asname,
                        'type': 'from_import'
                    })
        return imports

    def scan_python_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            tree = ast.parse(content)
            functions = []
            classes = []
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(self.analyze_function(node))
                elif isinstance(node, ast.ClassDef):
                    classes.append(self.analyze_class(node))
            constants = self.analyze_constants(tree)
            imports = self.analyze_imports(tree)
            return {
                'file_path': str(file_path),
                'functions': functions,
                'classes': classes,
                'constants': constants,
                'imports': imports,
                'total_functions': len(functions),
                'total_classes': len(classes),
                'total_constants': len(constants),
                'lines': len(content.splitlines()) if content else 0
            }
        except Exception as e:
            return {
                'file_path': str(file_path),
                'error': str(e),
                'functions': [],
                'classes': [],
                'constants': [],
                'imports': [],
                'total_functions': 0,
                'total_classes': 0,
                'total_constants': 0,
                'lines': 0
            }

    def should_skip_directory(self, dir_path):
        skip_dirs = {
            '__pycache__', '.git', '.svn', '.hg',
            'node_modules', '.venv', 'venv', 'env',
            '.pytest_cache', '.mypy_cache', '.tox',
            'build', 'dist', '.egg-info', 'htmlcov',
            '.coverage', '.idea', '.vscode', '.DS_Store'
        }
        return dir_path.name in skip_dirs or dir_path.name.startswith('.')

    def build_directory_structure(self):
        def process_directory(dir_path, max_depth=10, current_depth=0):
            if current_depth >= max_depth:
                return {'folders': {}, 'files': {}, 'error': 'Max depth reached'}
            result = {'folders': {}, 'files': {}}
            try:
                items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                for item in items:
                    if self.should_skip_directory(item) if item.is_dir() else item.name.startswith('.'):
                        continue
                    if item.is_dir():
                        result['folders'][item.name] = process_directory(
                            item, max_depth, current_depth + 1
                        )
                    elif item.suffix == '.py':
                        file_analysis = self.scan_python_file(item)
                        result['files'][item.name] = file_analysis
            except PermissionError:
                result['error'] = 'Permission denied'
            except Exception as e:
                result['error'] = str(e)
            return result
        return process_directory(self.project_path)

# --- Flask App Routes ---

app = Flask(__name__)

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Blockchain Supply Chain</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            display: flex;
            height: 100vh;
            max-width: 100vw;
        }
        .header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: #2d2d30;
            color: white;
            padding: 15px 20px;
            border-bottom: 1px solid #3e3e42;
            z-index: 1000;
        }
        .header h1 {
            color: #569cd6;
            font-size: 1.5rem;
            margin-bottom: 5px;
        }
        .main-content {
            display: flex;
            width: 100%;
            margin-top: 80px;
        }
        .sidebar {
            width: 300px;
            background: #252526;
            border-right: 1px solid #3e3e42;
            overflow-y: auto;
            height: calc(100vh - 80px);
        }
        .function-list {
            width: 350px;
            background: #1e1e1e;
            border-right: 1px solid #3e3e42;
            overflow-y: auto;
            height: calc(100vh - 80px);
        }
        .content-area {
            flex: 1;
            background: #1e1e1e;
            position: relative;
            height: calc(100vh - 80px);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .function-details {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        .deploy-panel {
            max-height: 300px;
            min-height: 150px
            background: #2d2d30;
            border-top: 2px solid #007acc;
            padding: 15px;
            overflow-y: auto;
        }
        .tree-item {
            user-select: none;
        }
        .tree-folder {
            padding: 6px 12px;
            display: flex;
            align-items: center;
            color: #cccccc;
            cursor: pointer;
        }
        .tree-folder:hover {
            background: #2a2d2e;
        }
        .tree-folder.expanded {
            color: #9cdcfe;
        }
        .tree-file {
            padding: 4px 12px 4px 24px;
            color: #d4d4d4;
            font-size: 0.9rem;
            cursor: pointer;
        }
        .tree-file:hover {
            background: #2a2d2e;
        }
        .tree-file.selected {
            background: #094771;
            color: #ffffff;
        }
        .tree-children {
            display: none;
            margin-left: 16px;
        }
        .tree-children.expanded {
            display: block;
        }
        .folder-icon::before {
            content: "📁 ";
            margin-right: 6px;
        }
        .folder-icon.expanded::before {
            content: "📂 ";
            margin-right: 6px;
        }
        .file-icon::before {
            content: "🐍 ";
            margin-right: 6px;
        }
        .function-list-header {
            background: #264f78;
            color: white;
            padding: 12px;
            font-weight: bold;
            border-bottom: 1px solid #3e3e42;
        }
        .function-item {
            padding: 12px;
            border-bottom: 1px solid #3e3e42;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .function-item:hover {
            background: #2a2d2e;
        }
        .function-item.selected {
            background: #094771;
            border-left: 3px solid #007acc;
        }
        .function-name {
            color: #dcdcaa;
            font-weight: bold;
            font-size: 1rem;
            margin-bottom: 4px;
        }
        .function-signature {
            color: #4ec9b0;
            font-size: 0.85rem;
            font-family: 'Courier New', monospace;
            margin-bottom: 4px;
        }
        .function-meta {
            font-size: 0.75rem;
            color: #9cdcfe;
        }
        .detailed-function {
            background: #2d2d30;
            border: 1px solid #3e3e42;
            border-radius: 6px;
            margin-bottom: 20px;
            padding: 20px;
        }
        .detailed-function.highlighted {
            border-color: #007acc;
            box-shadow: 0 0 10px rgba(0, 122, 204, 0.3);
        }
        .detailed-name {
            color: #dcdcaa;
            font-size: 1.3rem;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .detailed-signature {
            background: #1e1e1e;
            padding: 10px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            color: #4ec9b0;
            margin-bottom: 15px;
        }
        .param-list {
            margin-bottom: 15px;
        }
        .param-list h4 {
            color: #569cd6;
            margin-bottom: 8px;
        }
        .param {
            background: #1e1e1e;
            padding: 8px 12px;
            margin: 4px 0;
            border-radius: 4px;
            border-left: 3px solid #608b4e;
        }
        .param-name {
            color: #9cdcfe;
            font-weight: bold;
        }
        .param-type {
            color: #ce9178;
            margin-left: 8px;
        }
        .return-info {
            background: #1e1e1e;
            padding: 10px 12px;
            border-radius: 4px;
            border-left: 3px solid #ce9178;
        }
        .return-type {
            color: #b5cea8;
            font-weight: bold;
        }
        .deploy-header {
            color: #007acc;
            font-weight: bold;
            margin-bottom: 10px;
            text-align: center;
        }
        .deploy-button {
            width: 100%;
            background: linear-gradient(135deg, #007acc, #005a9e);
            color: white;
            border: none;
            padding: 10px;
            border-radius: 4px;
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 15px;
        }
        .deploy-button:hover {
            background: linear-gradient(135deg, #005a9e, #004578);
        }
        .deploy-list {
            max-height: 120px;
            overflow-y: auto;
        }
        .deploy-item {
            background: #1e1e1e;
            padding: 8px;
            margin: 4px 0;
            border-radius: 4px;
            font-size: 0.8rem;
            cursor: pointer;
        }
        .deploy-item.selected {
            background: #094771;
            border-left: 2px solid #007acc;
        }
        .loading {
            text-align: center;
            padding: 50px;
            color: #9cdcfe;
        }
        .no-selection {
            text-align: center;
            padding: 50px;
            color: #6a9955;
        }
        .decorator-tag {
            background: #f39c12;
            color: #2c3e50;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.7rem;
            margin-right: 4px;
            display: inline-block;
        }
        .async-tag {
            background: #e74c3c;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.7rem;
            margin-right: 4px;
        }
        .deploy-options {
            padding: 10px;
            border-bottom: 1px solid #3e3e42;
            color: #d4d4d4;
        }
        .deploy-options label {
            display: block;
            margin-bottom: 8px;
        }
        .deploy-options input[type="checkbox"] {
            margin-right: 8px;
        }
        .input-group {
            margin-bottom: 10px;
        }
        .input-group input[type="text"] {
            background: #1e1e1e;
            border: 1px solid #3e3e42;
            color: #fff;
            padding: 6px;
            width: 90%;
            border-radius: 4px;
        }
        .input-group label {
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Blockchain Supply Chain</h1>
        <p>Import this into your SCM / ERP tool to deploy specific smart contracts</p>
    </div>
    <div class="container">
        <div class="main-content">
            <div class="sidebar">
                <div id="loading" class="loading">Analyzing Python project structure...</div>
                <div id="file-tree" style="display: none;"></div>
            </div>
            <div class="function-list">
                <div class="function-list-header">Functions & Classes</div>
                <div id="function-list-content">
                    <div class="no-selection">Select a Python file to view its code elements</div>
                </div>
            </div>
            <div class="content-area">
                <div class="function-details" id="function-details">
                    <div class="no-selection">Select a function or class to view detailed information</div>
                </div>
                <div class="deploy-panel">
                    <div class="deploy-header">Web3 Deploy</div>
                    <div id="deploy-options-container" class="deploy-options" style="display: none;">
                        <label>
                            <input type="checkbox" id="encrypt-checkbox"> Encrypt Parameters
                        </label>
                        <div id="param-selection-container"></div>
                    </div>
                    <button class="deploy-button" onclick="deployToBlockchain()">Deploy Selected</button>
                    <div class="deploy-list" id="deploy-list">
                        <div style="text-align: center; color: #6a9955; font-size: 0.8rem;">
                            Select functions to deploy on-chain
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        let allData = {};
        let selectedFunctions = [];
        let currentFile = null;
        let lastSelectedElement = null;

        console.log('Fetching project structure...');
        fetch('/structure')
            .then(response => {
                console.log('Received response from /structure:', response);
                return response.json();
            })
            .then(data => {
                console.log('Successfully loaded project data:', data);
                allData = data;
                buildFileTree(data);
                document.getElementById('loading').style.display = 'none';
                document.getElementById('file-tree').style.display = 'block';
            })
            .catch(error => {
                console.error('Error loading project data:', error);
                document.getElementById('loading').innerHTML = 'Error loading data: ' + error;
            });

        function buildFileTree(structure) {
            let html = buildFolderHTML('Project Root', structure, '');
            document.getElementById('file-tree').innerHTML = html;
        }

        function buildFolderHTML(name, data, path) {
            let html = `
            <div class="tree-item">
                <div class="tree-folder folder-icon" onclick="toggleFolder(this)">
                    ${name}
                </div>
                <div class="tree-children">
            `;
            for (let [folderName, folderData] of Object.entries(data.folders || {})) {
                html += buildFolderHTML(folderName, folderData, `${path}/${folderName}`);
            }
            for (let [fileName, fileData] of Object.entries(data.files || {})) {
                const fileKey = path ? `${path}/${fileName}` : fileName;
                html += `
                <div class="tree-file file-icon" onclick="selectFile('${fileKey}')">
                    ${fileName}
                    <span style="color: #6a9955; font-size: 0.7rem; margin-left: 8px;">
                        ${fileData.total_functions}f ${fileData.total_classes}c
                    </span>
                </div>
                `;
            }
            html += '</div></div>';
            return html;
        }

        function toggleFolder(element) {
            const children = element.nextElementSibling;
            const isExpanded = children.classList.contains('expanded');
            if (isExpanded) {
                children.classList.remove('expanded');
                element.classList.remove('expanded');
            } else {
                children.classList.add('expanded');
                element.classList.add('expanded');
            }
        }

        function selectFile(filePath) {
            console.log('File selected:', filePath);
            document.querySelectorAll('.tree-file.selected').forEach(el => {
                el.classList.remove('selected');
            });
            event.target.closest('.tree-file').classList.add('selected');
            currentFile = filePath;
            const fileData = getFileData(filePath);
            displayFunctions(fileData, filePath);
        }

        function getFileData(filePath) {
            const pathParts = filePath.split('/').filter(p => p);
            let current = allData;
            for (let i = 0; i < pathParts.length - 1; i++) {
                current = current.folders[pathParts[i]];
                if (!current) return null;
            }
            const fileName = pathParts[pathParts.length - 1];
            return current.files ? current.files[fileName] : null;
        }

        function displayFunctions(fileData, fileName) {
            if (!fileData) {
                console.warn('No file data found.');
                return;
            }
            console.log('Displaying functions for file:', fileName, fileData);
            let html = '';
            const allElements = [];
            fileData.functions.forEach(func => {
                func.type = 'function';
                allElements.push(func);
            });
            fileData.classes.forEach(cls => {
                cls.type = 'class';
                allElements.push(cls);
                cls.methods.forEach(method => {
                    method.type = 'method';
                    method.className = cls.name;
                    allElements.push(method);
                });
            });
            if (allElements.length === 0) {
                html = '<div class="no-selection">No functions or classes found in this file</div>';
            } else {
                allElements.forEach((element, index) => {
                    let signature = element.name;
                    let icon = '⚡';
                    let typeLabel = 'Function';
                    if (element.type === 'class') {
                        icon = '🏛️';
                        typeLabel = 'Class';
                        signature += ` (${element.methods.length} methods)`;
                    } else if (element.type === 'method') {
                        icon = '🔧';
                        typeLabel = 'Method';
                        signature = element.className + '.' + element.name;
                        if (element.args && element.args.length > 0) {
                            signature += '(' + element.args.map(arg =>
                                arg.type ? `${arg.name}: ${arg.type}` : arg.name
                            ).join(', ') + ')';
                        } else {
                            signature += '()';
                        }
                    } else {
                        if (element.args && element.args.length > 0) {
                            signature += '(' + element.args.map(arg =>
                                arg.type ? `${arg.name}: ${arg.type}` : arg.name
                            ).join(', ') + ')';
                        } else {
                            signature += '()';
                        }
                    }
                    if (element.return_type) {
                        signature += ` -> ${element.return_type}`;
                    }
                    html += `
                    <div class="function-item" onclick="selectFunction(${index})">
                        <div class="function-name">
                            ${icon} ${element.name}
                            ${element.is_async ? '<span class="async-tag">async</span>' : ''}
                            ${element.decorators && element.decorators.length > 0 ?
                                element.decorators.map(d => `<span class="decorator-tag">@${d}</span>`).join('') : ''}
                        </div>
                        <div class="function-signature">${signature}</div>
                        <div class="function-meta">${typeLabel} • Line ${element.line}</div>
                    </div>
                    `;
                });
            }
            document.getElementById('function-list-content').innerHTML = html;
            window.currentElements = allElements;
        }

        function selectFunction(index) {
            console.log('Function selected with index:', index);
            document.querySelectorAll('.function-item.selected').forEach(el => {
                el.classList.remove('selected');
            });
            event.target.closest('.function-item').classList.add('selected');
            const element = window.currentElements[index];
            lastSelectedElement = element;
            displayFunctionDetails(element);
        }

        function displayFunctionDetails(element) {
            console.log('Displaying details for element:', element);
            let signature = element.name;
            let isDeployable = false;

            if (element.type === 'class') {
                signature = `class ${element.name}`;
                if (element.bases && element.bases.length > 0) {
                    signature += `(${element.bases.join(', ')})`;
                }
            } else {
                isDeployable = true;
                if (element.is_async) signature = 'async ' + signature;
                if (element.args && element.args.length > 0) {
                    signature += '(' + element.args.map(arg =>
                        arg.type ? `${arg.name}: ${arg.type}` : arg.name
                    ).join(', ') + ')';
                } else {
                    signature += '()';
                }
                if (element.return_type) {
                    signature += ` -> ${element.return_type}`;
                }
            }

            let html = `
            <div class="detailed-function highlighted">
                <div class="detailed-name">${element.className ? element.className + '.' : ''}${element.name}</div>
                <div class="detailed-signature">${signature}</div>
            `;

            if (element.decorators && element.decorators.length > 0) {
                html += `<div style="margin-bottom: 15px;">`;
                element.decorators.forEach(decorator => {
                    html += `<span class="decorator-tag">@${decorator}</span>`;
                });
                html += '</div>';
            }

            if (element.args && element.args.length > 0) {
                html += '<div class="param-list"><h4>Parameters:</h4>';
                element.args.forEach(arg => {
                    html += `
                    <div class="param">
                        <span class="param-name">${arg.name}</span>
                        <span class="param-type">${arg.type || 'any'}</span>
                    </div>
                    `;
                });
                html += '</div>';
            }

            if (element.type === 'class' && element.methods && element.methods.length > 0) {
                html += '<div class="param-list"><h4>Methods:</h4>';
                element.methods.forEach(method => {
                    html += `
                    <div class="param">
                        <span class="param-name">${method.name}</span>
                        <span class="param-type">${method.args ? method.args.length : 0} args</span>
                    </div>
                    `;
                });
                html += '</div>';
            }

            html += `
            <div class="return-info">
                <strong>Returns:</strong> <span class="return-type">${element.return_type || 'void'}</span>
            </div>
            `;

            if (element.docstring && element.docstring !== 'No documentation') {
                html += `
                <div style="margin-top: 15px; padding: 10px; background: #1e1e1e; border-radius: 4px;">
                    <strong style="color: #569cd6;">Documentation:</strong><br>
                    <span style="color: #6a9955;">${element.docstring}</span>
                </div>
                `;
            }
            html += '</div>';
            document.getElementById('function-details').innerHTML = html;

            const deployOptionsContainer = document.getElementById('deploy-options-container');
            const paramSelectionContainer = document.getElementById('param-selection-container');
            if (isDeployable) {
                deployOptionsContainer.style.display = 'block';
                paramSelectionContainer.innerHTML = '';
                if (element.args && element.args.length > 0) {
                    paramSelectionContainer.innerHTML += '<h4>Inputs to include:</h4>';
                    element.args.forEach((arg, index) => {
                        paramSelectionContainer.innerHTML += `
                            <div class="input-group">
                                <label>
                                    <input type="checkbox" name="param-include" value="${index}"> ${arg.name} (${arg.type || 'any'})
                                </label>
                                <input type="text" id="input-value-${index}" placeholder="Enter value">
                            </div>
                        `;
                    });
                }
                if (element.return_type && element.return_type !== 'void') {
                    paramSelectionContainer.innerHTML += `
                        <h4>Return value to include:</h4>
                        <label>
                            <input type="checkbox" name="param-include" value="output"> Output: ${element.return_type}
                        </label>
                    `;
                }
            } else {
                deployOptionsContainer.style.display = 'none';
            }

            if (element.type === 'function' || element.type === 'method') {
                addToDeployList(element);
            }
        }

        function addToDeployList(func) {
            const funcId = `${func.className || ''}.${func.name}`;
            if (selectedFunctions.some(f => f.id === funcId)) {
                return;
            }
            selectedFunctions.push({
                id: funcId,
                name: func.name,
                path: currentFile,
                className: func.className,
                args: lastSelectedElement.args,
                return_type: lastSelectedElement.return_type
            });
            renderDeployList();
        }

        function renderDeployList() {
            console.log('Rendering deploy list. Selected functions:', selectedFunctions);
            const deployList = document.getElementById('deploy-list');
            let html = '';
            if (selectedFunctions.length === 0) {
                html = `<div style="text-align: center; color: #6a9955; font-size: 0.8rem;">
                            Select functions to deploy on-chain
                        </div>`;
            } else {
                selectedFunctions.forEach((func, index) => {
                    html += `
                    <div class="deploy-item" onclick="removeFromDeployList(${index})">
                        ${func.className ? func.className + '.' : ''}${func.name}
                        <span style="float: right; color: #e74c3c;">(X)</span>
                    </div>
                    `;
                });
            }
            deployList.innerHTML = html;
        }

        function removeFromDeployList(index) {
            console.log('Removing function from deploy list at index:', index);
            selectedFunctions.splice(index, 1);
            renderDeployList();
        }

        function deployToBlockchain() {
            if (selectedFunctions.length === 0) {
                console.warn('Please select at least one function to deploy.');
                return;
            }

            const encryptOption = document.getElementById('encrypt-checkbox').checked;
            const paramSelectionContainer = document.getElementById('param-selection-container');
            const includedParams = [];
            let isValid = true;

            // Fix the regex to avoid SyntaxWarning
            const intRegex = /^-?\d+$/;

            // Iterate through each input group to validate and collect data
            if (lastSelectedElement && lastSelectedElement.args) {
                lastSelectedElement.args.forEach((arg, index) => {
                    const checkbox = paramSelectionContainer.querySelector(`input[type="checkbox"][value="${index}"]`);
                    if (checkbox && checkbox.checked) {
                        const valueElement = document.getElementById(`input-value-${index}`);
                        let value = valueElement.value;
                        let type = arg.type;

                        if (type === 'int') {
                            if (!intRegex.test(value)) {
                                console.error(`Validation Error: Value for '${arg.name}' must be an integer.`);
                                isValid = false;
                                return;
                            }
                        } else if (type === 'bool') {
                            if (value.toLowerCase() !== 'true' && value.toLowerCase() !== 'false') {
                                console.error(`Validation Error: Value for '${arg.name}' must be 'true' or 'false'.`);
                                isValid = false;
                                return;
                            }
                        }

                        includedParams.push({
                            name: arg.name,
                            type: type,
                            value: value
                        });
                    }
                });
            }


            // Handle return value if selected
            const returnCheckbox = paramSelectionContainer.querySelector('input[type="checkbox"][value="output"]');
            if (returnCheckbox && returnCheckbox.checked) {
                 includedParams.push({
                    name: 'return',
                    type: lastSelectedElement.return_type,
                    value: 'N/A'
                });
            }

            if (!isValid) {
                console.error("Deployment aborted due to validation errors.");
                return;
            }

            const payload = selectedFunctions.map(f => {
                return {
                    file: f.path,
                    className: f.className,
                    functionName: f.name,
                    encrypt: encryptOption,
                    included_params: includedParams,
                    encrypt_return: includedParams.some(p => p.name === 'return'),
                    args: f.args,
                    return_type: f.return_type
                };
            });

            console.log('Sending deployment request with payload:', payload);
            fetch('/deploy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            })
            .then(response => {
                console.log('Received response from /deploy:', response);
                return response.json();
            })
            .then(data => {
                console.log('Deployment successful. Server response:', data);
                if (data.results && data.results[0] && data.results[0].deployment_output) {
                    console.log('--- Forge CLI Output Start ---');
                    console.log(data.results[0].deployment_output);
                    console.log('--- Forge CLI Output End ---');
                }
                selectedFunctions = [];
                renderDeployList();
            })
            .catch(error => {
                console.error('Deployment failed:', error);
            });
        }
    </script>
</body>
</html>
'''

# --- Smart Contract Generation and Deployment Logic ---

def python_to_solidity_type(py_type):
    """Maps Python types to a suitable Solidity type (simplified)."""
    if py_type in ('int', 'int64', 'int32'):
        return 'int256'
    if py_type in ('str', 'string'):
        return 'string'
    if py_type == 'bool':
        return 'bool'
    if py_type in ('float', 'float64'):
        return 'string' # Using string as a simple representation for float
    # Fallback for unsupported types or complex types
    return 'string'

def generate_solidity_contract(req):
    """Dynamically generates a simple Solidity contract based on request data."""
    func_name = req.get('functionName')

    # Clean function name for Solidity identifier
    sol_func_name = re.sub(r'[^a-zA-Z0-9_]', '', func_name)
    contract_name = f"{sol_func_name.capitalize()}Record"

    # Define state variables
    state_vars = []
    # For each included parameter, create a public state variable
    for param in req.get('included_params', []):
        if param['name'] == 'return':
            sol_type = python_to_solidity_type(param.get('type'))
            state_vars.append(f"    {sol_type} public returnValue;")
        else:
            sol_type = python_to_solidity_type(param.get('type'))
            state_vars.append(f"    {sol_type} public {param.get('name')};")

    # Define constructor to initialize the state variables
    constructor_params = []
    constructor_logic = []
    for param in req.get('included_params', []):
        sol_type = python_to_solidity_type(param.get('type'))

        # Don't add return value to constructor
        if param['name'] == 'return':
            continue

        if sol_type == 'string':
            constructor_params.append(f"{sol_type} memory _{param.get('name')}")
        else:
            constructor_params.append(f"{sol_type} _{param.get('name')}")
        constructor_logic.append(f"        {param.get('name')} = _{param.get('name')};")

    constructor_params_str = ", ".join(constructor_params)
    constructor_logic_str = "\n".join(constructor_logic)

    sol_code = f"""
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract {contract_name} {{
{'''
'''.join(state_vars)}

    constructor({constructor_params_str}) {{
{constructor_logic_str}
    }}
}}
"""
    return sol_code, contract_name

def generate_and_run_forge_script(sol_code, contract_name, constructor_args, encrypt_flag):
    """
    Creates and runs a bash script to deploy the contract using forge.
    Assumes forge is installed and configured.
    """
    # Apply encryption and format arguments for forge
    final_args = []
    for arg in constructor_args:
        # Skip 'N/A' as it's for return values
        if arg == 'N/A':
            continue

        # Check if the value is a string that represents a number or bool
        if isinstance(arg, str):
            if re.match(r'^-?\d+$', arg):
                final_args.append(arg)
            elif arg.lower() in ['true', 'false']:
                final_args.append(arg.lower())
            else:
                final_args.append(f"'{basic_encrypt(arg)}'" if encrypt_flag else f"'{arg}'")
        else:
            final_args.append(str(arg))

    constructor_args_str = " ".join(final_args)

    script_content = f"""#!/bin/bash

# A simple script to deploy the generated contract using Forge.
# It uses the environment variables from your .env file.

# Load environment variables
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create one with RPC_URL and PRIVATE_KEY."
    exit 1
fi
set -a
source .env
set +a

# Run the deployment command
echo "Running Forge deployment command..."
forge create --broadcast \\
    --rpc-url "$RPC_URL" \\
    --private-key "$PRIVATE_KEY" \\
    src/{contract_name}.sol:{contract_name} \\
    --constructor-args {constructor_args_str}

# Check if the deployment was successful
if [ $? -ne 0 ]; then
    echo "Forge deployment failed."
    exit 1
fi

echo "Deployment of {contract_name} successful."
"""
    os.makedirs('src', exist_ok=True)
    sol_path = Path('src') / f"{contract_name}.sol"
    with open(sol_path, 'w') as f:
        f.write(sol_code)

    deploy_script_path = Path('deploy.sh')
    with open(deploy_script_path, 'w') as f:
        f.write(script_content)
    os.chmod(deploy_script_path, 0o755)

    try:
        result = subprocess.run(['./deploy.sh'], check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: Forge deployment script failed.\nStdout: {e.stdout}\nStderr: {e.stderr}"
    finally:
        pass

@app.route('/structure')
def get_structure():
    try:
        scanner = PythonProjectScanner()
        data = scanner.build_directory_structure()

        # Manually inject the hardcoded test directory and file
        test_dir = {'folders': {}, 'files': {}}
        test_dir['files']['sample_function.py'] = {
            'file_path': '(Test)/sample_function.py',
            'functions': [{
                'name': 'create_product_record',
                'line': 1,
                'args': [
                    {'name': 'product_id', 'type': 'str'},
                    {'name': 'product_name', 'type': 'str'},
                    {'name': 'price', 'type': 'int'},
                    {'name': 'is_available', 'type': 'bool'}
                ],
                'return_type': 'str',
                'decorators': ['@supply_chain.record'],
                'docstring': 'Creates a new product record on the blockchain.',
                'is_async': False
            }],
            'classes': [],
            'constants': [],
            'imports': [],
            'total_functions': 1,
            'total_classes': 0,
            'total_constants': 0,
            'lines': 10
        }

        if '(Test)' in data['folders']:
            data['folders']['(Test)']['files'].update(test_dir['files'])
        else:
            data['folders']['(Test)'] = test_dir

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/deploy', methods=['POST'])
def deploy():
    try:
        deployment_requests = request.json
        responses = []
        for req in deployment_requests:
            func_name = req.get('functionName')

            # Gather constructor arguments from included parameters
            included_params_raw = req.get('included_params', [])
            included_params_for_solidity = []
            constructor_args = []

            for param in included_params_raw:
                if param['name'] == 'return':
                    # Handle return value placeholder
                    included_params_for_solidity.append(param)
                else:
                    included_params_for_solidity.append(param)
                    constructor_args.append(param['value'])

            # Generate and deploy the smart contract
            req['included_params'] = included_params_for_solidity
            sol_code, contract_name = generate_solidity_contract(req)

            # Pass encryption flag to the deployment script generator
            encryption_flag = req.get('encrypt', False)
            deployment_output = generate_and_run_forge_script(sol_code, contract_name, constructor_args, encryption_flag)

            responses.append({
                'status': 'success',
                'message': f'Deployment of {func_name} prepared.',
                'solidity_contract': sol_code,
                'deployment_output': deployment_output,
                'encrypted_data_sent': encryption_flag,
                'included_params': included_params_for_solidity,
                'encrypt_return': req.get('encrypt_return', False)
            })

        return jsonify({
            'status': 'success',
            'message': 'Deployment process initiated for selected functions.',
            'results': responses
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/info')
def project_info():
    try:
        scanner = PythonProjectScanner()
        structure = scanner.build_directory_structure()
        total_files = 0
        total_functions = 0
        total_classes = 0
        def count_recursive(data):
            nonlocal total_files, total_functions, total_classes
            for file_data in data.get('files', {}).values():
                total_files += 1
                total_functions += file_data.get('total_functions', 0)
                total_classes += file_data.get('total_classes', 0)
            for folder_data in data.get('folders', {}).values():
                count_recursive(folder_data)
        count_recursive(structure)
        return jsonify({
            'project_path': str(scanner.project_path),
            'total_files': total_files,
            'total_functions': total_functions,
            'total_classes': total_classes
        })
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = find_free_port(8003)
    print(f"Starting Blockchain Supply Chain on http://localhost:{port}")
    print("This tool works with any Python project structure!")

    # Create the (Test) directory and sample file if they don't exist
    test_dir_path = Path('(Test)')
    if not test_dir_path.exists():
        os.makedirs(test_dir_path)

    test_file_path = test_dir_path / 'sample_function.py'
    if not test_file_path.exists():
        with open(test_file_path, 'w') as f:
            f.write(
                """
def create_product_record(product_id: str, product_name: str, price: int, is_available: bool) -> str:
    \"\"\"
    A sample function that creates a new product record.
    This function demonstrates the ideal structure for a deployable smart contract.
    It takes four parameters and returns a string message.
    \"\"\"
    # This is a mock function, the actual logic would interact with a database or API
    return f"Product {product_name} with ID {product_id} recorded."
"""
            )
    app.run(debug=True, port=port, host='0.0.0.0')
