import os
import json
import re
import shutil
from datetime import datetime
from flask import current_app

VALID_WORKSPACE_NAME_REGEX = re.compile(r'^[a-zA-Z0-9_\- ]{1,64}$')

def get_workspaces_root():
    root = current_app.config.get('WORKSPACES_DIR')
    if not root:
        root = os.path.join(current_app.config.get('DATA_DIR', 'MrStrictData'), 'workspaces')
    os.makedirs(root, exist_ok=True)
    return os.path.abspath(root)

def sanitize_workspace_name(name):
    if not name or not isinstance(name, str):
        return None
    name = name.strip()
    if not VALID_WORKSPACE_NAME_REGEX.match(name):
        return None
    # Disallow path navigation names
    if name in ('.', '..', '/', '\\') or '..' in name:
        return None
    return name

def get_workspace_dir(name):
    clean_name = sanitize_workspace_name(name)
    if not clean_name:
        raise ValueError("Invalid workspace name.")
    root = get_workspaces_root()
    ws_dir = os.path.abspath(os.path.join(root, clean_name))
    # Path traversal check
    if not ws_dir.startswith(root) or ws_dir == root:
        raise ValueError("Path traversal violation.")
    return ws_dir

def list_workspaces():
    root = get_workspaces_root()
    workspaces = []
    if not os.path.exists(root):
        return workspaces
    for entry in os.listdir(root):
        full_path = os.path.join(root, entry)
        if os.path.isdir(full_path) and not entry.startswith('.'):
            meta_path = os.path.join(full_path, 'workspace.json')
            created_at = None
            description = ""
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        created_at = data.get('created_at')
                        description = data.get('description', '')
                except:
                    pass
            workspaces.append({
                'name': entry,
                'path': full_path,
                'created_at': created_at or datetime.fromtimestamp(os.path.getctime(full_path)).strftime('%Y-%m-%d %H:%M'),
                'description': description
            })
    return sorted(workspaces, key=lambda x: x['name'].lower())

def create_workspace(name, description=""):
    clean_name = sanitize_workspace_name(name)
    if not clean_name:
        raise ValueError("Invalid workspace name. Use 1-64 alphanumeric characters, underscores, spaces, or hyphens.")
    
    ws_dir = get_workspace_dir(clean_name)
    if os.path.exists(ws_dir):
        raise ValueError(f"Workspace '{clean_name}' already exists.")

    # Create local storage layout
    subdirs = [
        os.path.join('uploads', 'answer_keys'),
        os.path.join('uploads', 'student_submissions'),
        'results',
        'reports',
        'exports',
        'backups'
    ]
    for sub in subdirs:
        os.makedirs(os.path.join(ws_dir, sub), exist_ok=True)

    meta = {
        'name': clean_name,
        'description': description,
        'created_at': datetime.utcnow().isoformat(),
        'version': '1.0'
    }
    with open(os.path.join(ws_dir, 'workspace.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    return clean_name

def workspace_exists(name):
    try:
        ws_dir = get_workspace_dir(name)
        return os.path.exists(ws_dir) and os.path.isdir(ws_dir)
    except:
        return False

def ensure_workspace_layout(name):
    ws_dir = get_workspace_dir(name)
    subdirs = [
        os.path.join('uploads', 'answer_keys'),
        os.path.join('uploads', 'student_submissions'),
        'results',
        'reports',
        'exports',
        'backups'
    ]
    for sub in subdirs:
        os.makedirs(os.path.join(ws_dir, sub), exist_ok=True)
    return ws_dir

def backup_workspace(name, destination_folder=None):
    ws_dir = get_workspace_dir(name)
    if not os.path.exists(ws_dir):
        raise ValueError("Workspace does not exist.")

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"backup_{name}_{timestamp}.zip"
    
    if not destination_folder:
        target_dir = os.path.join(ws_dir, 'backups')
    else:
        target_dir = os.path.abspath(destination_folder)
        os.makedirs(target_dir, exist_ok=True)
        
    archive_base = os.path.join(target_dir, f"backup_{name}_{timestamp}")
    shutil.make_archive(archive_base, 'zip', ws_dir)
    return f"{archive_base}.zip"
