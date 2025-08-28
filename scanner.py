#!/usr/bin/env python3
"""
Supply Chain Explorer with Web3 Deploy Panel
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

class SimpleChainScanner:
    def __init__(self, bench_path=None):
        if bench_path is None:
            current = Path.cwd()
            if (current / 'sites').exists():
                self.bench_path = current
            else:
                # Try to find Chain-bench
                for parent in current.parents:
                    if (parent / 'sites').exists():
                        self.bench_path = parent
                        break
                else:
                    self.bench_path = current
        else:
            self.bench_path = Path(bench_path)

        self.apps_path = self.bench_path / 'apps'

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

        return_type = None
        if func_node.returns:
            try:
                return_type = ast.unparse(func_node.returns)
            except:
                return_type = 'unknown'

        return {
            'name': func_node.name,
            'line': func_node.lineno,
            'args': args,
            'return_type': return_type,
            'docstring': ast.get_docstring(func_node) or 'No documentation'
        }

    def scan_python_file(self, file_path):
        """Analyze a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            functions = []
            classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(self.analyze_function(node))
                elif isinstance(node, ast.ClassDef):
                    class_methods = []
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            class_methods.append(self.analyze_function(child))

                    classes.append({
                        'name': node.name,
                        'line': node.lineno,
                        'methods': class_methods,
                        'docstring': ast.get_docstring(node) or 'No documentation'
                    })

            return {
                'file_path': str(file_path),
                'functions': functions,
                'classes': classes,
                'total_functions': len(functions),
                'total_classes': len(classes)
            }

        except Exception as e:
            return {
                'file_path': str(file_path),
                'error': str(e),
                'functions': [],
                'classes': [],
                'total_functions': 0,
                'total_classes': 0
            }

    def build_folder_structure(self):
        """Build hierarchical folder structure"""
        structure = {}

        if not self.apps_path.exists():
            return structure

        for app_dir in self.apps_path.iterdir():
            if not app_dir.is_dir() or app_dir.name.startswith('.'):
                continue

            app_structure = self.build_app_structure(app_dir)
            structure[app_dir.name] = app_structure

        return structure

    def build_app_structure(self, app_path):
        """Build folder structure for a single app"""

        def process_directory(dir_path):
            result = {'folders': {}, 'files': {}}

            try:
                for item in dir_path.iterdir():
                    if item.name.startswith('.') or item.name == '__pycache__':
                        continue

                    if item.is_dir():
                        result['folders'][item.name] = process_directory(item)
                    elif item.suffix == '.py':
                        file_analysis = self.scan_python_file(item)
                        result['files'][item.name] = file_analysis

            except PermissionError:
                result['error'] = 'Permission denied'

            return result

        return process_directory(app_path)

app = Flask(__name__)

@app.route('/')
def index():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Supply Chain Explorer</title>
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
    </style>
</head>
<body>
    <div class="header">
        <h1>Supply Chain Function Explorer</h1>
        <p>Navigate files, explore functions, deploy to blockchain</p>
    </div>

    <div class="container">
        <div class="main-content">
            <div class="sidebar">
                <div id="loading" class="loading">Loading directory structure...</div>
                <div id="file-tree" style="display: none;"></div>
            </div>

            <div class="function-list">
                <div class="function-list-header">Functions</div>
                <div id="function-list-content">
                    <div class="no-selection">Select a Python file to view its functions</div>
                </div>
            </div>

            <div class="content-area">
                <div class="function-details" id="function-details">
                    <div class="no-selection">Select a function to view detailed information</div>
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
            let html = '';
            for (let [appName, appData] of Object.entries(structure)) {
                html += buildFolderHTML(appName, appData, appName);
            }
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

            // Add folders
            for (let [folderName, folderData] of Object.entries(data.folders || {})) {
                html += buildFolderHTML(folderName, folderData, `${path}/${folderName}`);
            }

            // Add files
            for (let [fileName, fileData] of Object.entries(data.files || {})) {
                html += `
                <div class="tree-file file-icon" onclick="selectFile('${path}', '${fileName}')">
                    ${fileName}
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

        function selectFile(path, fileName) {
            // Remove previous selection
            document.querySelectorAll('.tree-file.selected').forEach(el => {
                el.classList.remove('selected');
            });

            // Add selection
            event.target.classList.add('selected');

            currentFile = `${path}/${fileName}`;
            const fileData = getFileData(path, fileName);
            displayFunctions(fileData, fileName);
        }

        function getFileData(path, fileName) {
            const pathParts = path.split('/');
            let current = allData;

            for (let part of pathParts) {
                if (current[part]) {
                    current = current[part];
                } else if (current.folders && current.folders[part]) {
                    current = current.folders[part];
                }
            }

            return current.files ? current.files[fileName] : null;
        }

        function displayFunctions(fileData, fileName) {
            if (!fileData) return;

            let html = '';
            const allFunctions = [...fileData.functions];

            // Add class methods
            fileData.classes.forEach(cls => {
                cls.methods.forEach(method => {
                    method.className = cls.name;
                    allFunctions.push(method);
                });
            });

            if (allFunctions.length === 0) {
                html = '<div class="no-selection">No functions found in this file</div>';
            } else {
                allFunctions.forEach((func, index) => {
                    let signature = func.name + '(';
                    if (func.args && func.args.length > 0) {
                        signature += func.args.map(arg =>
                            arg.type ? `${arg.name}: ${arg.type}` : arg.name
                        ).join(', ');
                    }
                    signature += ')';
                    if (func.return_type) {
                        signature += ` -> ${func.return_type}`;
                    }

                    html += `
                    <div class="function-item" onclick="selectFunction(${index})">
                        <div class="function-name">${func.className ? func.className + '.' : ''}${func.name}</div>
                        <div class="function-signature">${signature}</div>
                        <div class="function-meta">Line ${func.line}</div>
                    </div>
                    `;
                });
            }

            document.getElementById('function-list-content').innerHTML = html;
            window.currentFunctions = allFunctions;
        }

        function selectFunction(index) {
            // Remove previous selection
            document.querySelectorAll('.function-item.selected').forEach(el => {
                el.classList.remove('selected');
            });

            // Add selection
            event.target.classList.add('selected');

            const func = window.currentFunctions[index];
            displayFunctionDetails(func);
        }

        function displayFunctionDetails(func) {
            let signature = func.name + '(';
            if (func.args && func.args.length > 0) {
                signature += func.args.map(arg =>
                    arg.type ? `${arg.name}: ${arg.type}` : arg.name
                ).join(', ');
            }
            signature += ')';
            if (func.return_type) {
                signature += ` -> ${func.return_type}`;
            }

            let html = `
            <div class="detailed-function highlighted">
                <div class="detailed-name">${func.className ? func.className + '.' : ''}${func.name}</div>
                <div class="detailed-signature">${signature}</div>
            `;

            if (func.args && func.args.length > 0) {
                html += '<div class="param-list"><h4>Parameters:</h4>';
                func.args.forEach(arg => {
                    html += `
                    <div class="param">
                        <span class="param-name">${arg.name}</span>
                        <span class="param-type">${arg.type || 'any'}</span>
                    </div>
                    `;
                });
                html += '</div>';
            }

            html += `
            <div class="return-info">
                <strong>Returns:</strong> <span class="return-type">${func.return_type || 'void'}</span>
            </div>
            `;

            if (func.docstring && func.docstring !== 'No documentation') {
                html += `
                <div style="margin-top: 15px; padding: 10px; background: #1e1e1e; border-radius: 4px;">
                    <strong style="color: #569cd6;">Documentation:</strong><br>
                    <span style="color: #6a9955;">${func.docstring}</span>
                </div>
                `;
            }

            html += '</div>';

            document.getElementById('function-details').innerHTML = html;

            // Add to deploy list if not already there
            addToDeployList(func);
        }

        function addToDeployList(func) {
            const funcId = `${func.className || ''}.${func.name}`;

            if (!selectedFunctions.find(f => f.id === funcId)) {
                selectedFunctions.push({
                    id: funcId,
                    name: func.name,
                    className: func.className,
                    args: func.args || [],
                    return_type: func.return_type,
                    selected: false
                });
                updateDeployList();
            }
        }

        function updateDeployList() {
            let html = '';

            selectedFunctions.forEach((func, index) => {
                html += `
                <div class="deploy-item ${func.selected ? 'selected' : ''}" onclick="toggleDeploySelection(${index})">
                    ${func.className ? func.className + '.' : ''}${func.name}
                    <div style="font-size: 0.7rem; color: #9cdcfe;">
                        ${func.args.length} inputs → ${func.return_type || 'void'}
                    </div>
                </div>
                `;
            });

            if (html === '') {
                html = '<div style="text-align: center; color: #6a9955; font-size: 0.8rem;">Select functions to deploy on-chain</div>';
            }

            document.getElementById('deploy-list').innerHTML = html;
        }

        function toggleDeploySelection(index) {
            selectedFunctions[index].selected = !selectedFunctions[index].selected;
            updateDeployList();
        }

        function deployToBlockchain() {
            const selected = selectedFunctions.filter(f => f.selected);

            if (selected.length === 0) {
                alert('Please select functions to deploy on-chain');
                return;
            }

            let message = 'Deploy to blockchain:\\n\\n';
            selected.forEach(func => {
                message += `• ${func.className ? func.className + '.' : ''}${func.name}\\n`;
                message += `  Inputs: ${func.args.map(a => a.name).join(', ') || 'none'}\\n`;
                message += `  Output: ${func.return_type || 'void'}\\n\\n`;
            });

            alert(message + 'Smart contract deployment coming soon!');
        }
    </script>
</body>
</html>
    '''

@app.route('/structure')
def get_structure():
    try:
        scanner = SimpleChainScanner()
        data = scanner.build_folder_structure()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    port = find_free_port(8003)
    print(f"Starting Supply Chain Explorer on http://localhost:{port}")
    app.run(debug=True, port=port, host='0.0.0.0')
