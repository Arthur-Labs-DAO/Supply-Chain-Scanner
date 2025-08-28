#!/usr/bin/env python3
"""
Blockchain Supply Chain
Import this into yur SCM / ERP tool to deploy specific smart contracts
"""

import os
import ast
from pathlib import Path
from flask import Flask, jsonify
import socket
from contextlib import closing

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
            # Auto-detect project root
            current = Path.cwd()
            # Look for common project indicators
            project_indicators = [
                'setup.py', 'pyproject.toml', 'requirements.txt',
                'Pipfile', 'poetry.lock', 'environment.yml',
                '.git', 'src', 'lib', 'app', 'apps'
            ]

            # Check current directory first
            if any((current / indicator).exists() for indicator in project_indicators):
                self.project_path = current
            else:
                # Check parent directories
                for parent in current.parents:
                    if any((parent / indicator).exists() for indicator in project_indicators):
                        self.project_path = parent
                        break
                else:
                    # Default to current directory if no indicators found
                    self.project_path = current
        else:
            self.project_path = Path(project_path)

        print(f"Scanning Python project at: {self.project_path}")

    def analyze_function(self, func_node):
        """Extract function information from AST node"""
        args = []
        for arg in func_node.args.args:
            arg_info = {'name': arg.arg, 'type': None}
            if arg.annotation:
                try:
                    arg_info['type'] = ast.unparse(arg.annotation)
                except:
                    arg_info['type'] = 'unknown'
            args.append(arg_info)

        # Handle *args
        if func_node.args.vararg:
            args.append({
                'name': f"*{func_node.args.vararg.arg}",
                'type': 'varargs'
            })

        # Handle **kwargs
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

        # Detect decorators
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
        """Extract class information from AST node"""
        methods = []
        attributes = []

        for child in class_node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self.analyze_function(child))
            elif isinstance(child, ast.Assign):
                # Class attributes
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

        # Get base classes
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
        """Extract module-level constants"""
        constants = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Only top-level assignments
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
        """Extract import information"""
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
        """Analyze a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            tree = ast.parse(content)
            functions = []
            classes = []

            # Only get top-level functions and classes
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
        """Check if directory should be skipped"""
        skip_dirs = {
            '__pycache__', '.git', '.svn', '.hg',
            'node_modules', '.venv', 'venv', 'env',
            '.pytest_cache', '.mypy_cache', '.tox',
            'build', 'dist', '.egg-info', 'htmlcov',
            '.coverage', '.idea', '.vscode', '.DS_Store'
        }
        return dir_path.name in skip_dirs or dir_path.name.startswith('.')

    def build_directory_structure(self):
        """Build hierarchical directory structure for any Python project"""

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
        }

        .function-details {
            height: 75%;
            overflow-y: auto;
            padding: 20px;
        }

        .deploy-panel {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 25%;
            height: 25%;
            background: #2d2d30;
            border: 2px solid #007acc;
            border-radius: 8px 0 0 0;
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

        // Load data on page load
        fetch('/structure')
            .then(response => response.json())
            .then(data => {
                allData = data;
                buildFileTree(data);
                document.getElementById('loading').style.display = 'none';
                document.getElementById('file-tree').style.display = 'block';
            })
            .catch(error => {
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

            // Add folders first
            for (let [folderName, folderData] of Object.entries(data.folders || {})) {
                html += buildFolderHTML(folderName, folderData, `${path}/${folderName}`);
            }

            // Add Python files
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
            // Remove previous selection
            document.querySelectorAll('.tree-file.selected').forEach(el => {
                el.classList.remove('selected');
            });

            // Add selection
            event.target.closest('.tree-file').classList.add('selected');

            currentFile = filePath;
            const fileData = getFileData(filePath);
            displayFunctions(fileData, filePath);
        }

        function getFileData(filePath) {
            const pathParts = filePath.split('/').filter(p => p);
            let current = allData;

            // Navigate through folders
            for (let i = 0; i < pathParts.length - 1; i++) {
                current = current.folders[pathParts[i]];
                if (!current) return null;
            }

            // Get the file
            const fileName = pathParts[pathParts.length - 1];
            return current.files ? current.files[fileName] : null;
        }

        function displayFunctions(fileData, fileName) {
            if (!fileData) return;

            let html = '';
            const allElements = [];

            // Add standalone functions
            fileData.functions.forEach(func => {
                func.type = 'function';
                allElements.push(func);
            });

            // Add classes and their methods
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
            // Remove previous selection
            document.querySelectorAll('.function-item.selected').forEach(el => {
                el.classList.remove('selected');
            });

            // Add selection
            event.target.closest('.function-item').classList.add('selected');

            const element = window.currentElements[index];
            displayFunctionDetails(element);
        }

        function displayFunctionDetails(element) {
            let signature = element.name;

            if (element.type === 'class') {
                signature = `class ${element.name}`;
                if (element.bases && element.bases.length > 0) {
                    signature += `(${element.bases.join(', ')})`;
                }
            } else {
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

            // Add to deploy list if it's a function or method
            if (element.type === 'function' || element.type === 'method') {
                addToDeployList(element);
            }
        }

        function addToDeployList(func) {
            const funcId = `${func.className || ''}.${func.name}`;

            // Check if function is already in the list
            if (selectedFunctions.some(f => f.id === funcId)) {
                return;
            }

            selectedFunctions.push({
                id: funcId,
                name: func.name,
                path: currentFile,
                className: func.className
            });

            renderDeployList();
        }

        function renderDeployList() {
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
            selectedFunctions.splice(index, 1);
            renderDeployList();
        }

        function deployToBlockchain() {
            if (selectedFunctions.length === 0) {
                alert('Please select at least one function to deploy.');
                return;
            }

            const payload = selectedFunctions.map(f => {
                const parts = f.id.split('.');
                return {
                    file: f.path,
                    className: f.className,
                    functionName: parts[parts.length - 1]
                };
            });

            fetch('/deploy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            })
            .then(response => response.json())
            .then(data => {
                alert('Deployment initiated: ' + JSON.stringify(data, null, 2));
                selectedFunctions = [];
                renderDeployList();
            })
            .catch(error => {
                alert('Deployment failed: ' + error);
            });
        }
    </script>
</body>
</html>
'''

@app.route('/structure')
def get_structure():
    try:
        scanner = PythonProjectScanner()
        data = scanner.build_directory_structure()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/deploy', methods=['POST'])
def deploy():
    # Placeholder for Web3 deployment logic
    from flask import request
    functions = request.json
    return jsonify({
        'status': 'success',
        'message': f'Deployment prepared for {len(functions)} functions',
        'functions': functions
    })

@app.route('/info')
def project_info():
    try:
        scanner = PythonProjectScanner()
        structure = scanner.build_directory_structure()

        # Count totals
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
    app.run(debug=True, port=port, host='0.0.0.0')
