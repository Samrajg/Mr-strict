from flask import Blueprint, render_template, request, flash, redirect, url_for, session, send_file
from app.auth_utils import login_required
from app.services import workspace_service
import os

workspace_bp = Blueprint('workspaces', __name__, url_prefix='/workspaces')

@workspace_bp.route('/', methods=['GET'])
@login_required
def index():
    workspaces = workspace_service.list_workspaces()
    active_ws = session.get('active_workspace', 'default')
    # If active workspace is not created on disk yet, ensure it exists
    if not workspace_service.workspace_exists(active_ws):
        try:
            workspace_service.create_workspace(active_ws, "Default Workspace")
        except:
            pass
        workspaces = workspace_service.list_workspaces()

    return render_template('workspaces/index.html', workspaces=workspaces, active_ws=active_ws, root_path=workspace_service.get_workspaces_root())

@workspace_bp.route('/create', methods=['POST'])
@login_required
def create():
    name = request.form.get('workspace_name', '').strip()
    description = request.form.get('description', '').strip()
    try:
        created = workspace_service.create_workspace(name, description)
        session['active_workspace'] = created
        flash(f"Workspace '{created}' created and set as active!", 'success')
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f"Could not create workspace: {str(e)}", 'error')
    return redirect(url_for('workspaces.index'))

@workspace_bp.route('/select/<name>', methods=['POST', 'GET'])
@login_required
def select(name):
    if workspace_service.workspace_exists(name):
        session['active_workspace'] = name
        flash(f"Active workspace switched to '{name}'.", 'success')
    else:
        flash("Workspace not found.", 'error')
    return redirect(url_for('workspaces.index'))

@workspace_bp.route('/backup/<name>', methods=['POST'])
@login_required
def backup(name):
    try:
        zip_path = workspace_service.backup_workspace(name)
        flash(f"Workspace backed up successfully! Saved to: {zip_path}", 'success')
    except Exception as e:
        flash(f"Backup failed: {str(e)}", 'error')
    return redirect(url_for('workspaces.index'))
