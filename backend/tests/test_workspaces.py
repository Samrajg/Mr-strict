import unittest
import os
import shutil
import tempfile
import json
import io
from app import create_app, db
from app.models import User, Assignment, Rubric, Submission, Student
from app.services import workspace_service
from config import Config

class TestWorkspaceConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key-for-local-prototype'
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

class LocalWorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        TestWorkspaceConfig.DATA_DIR = self.temp_dir
        TestWorkspaceConfig.WORKSPACES_DIR = os.path.join(self.temp_dir, 'workspaces')

        self.app = create_app(TestWorkspaceConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed demo user
        self.user = User(username='demo', email='demo@example.com')
        self.user.set_password('demo123')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def login(self, username='demo', password='demo123'):
        return self.client.post('/auth/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    # 1. Demo Login & Authentication
    def test_demo_login_success(self):
        res = self.login('demo', 'demo123')
        self.assertIn(b'Welcome back, demo!', res.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('username'), 'demo')

    def test_demo_login_failure(self):
        res = self.login('demo', 'wrongpass')
        self.assertIn(b'Invalid username or password', res.data)

    # 2. Workspace Creation & Layout
    def test_workspace_creation_and_layout(self):
        self.login()
        res = self.client.post('/workspaces/create', data={
            'workspace_name': 'My_Class_2026',
            'description': 'Spring Semester 2026'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My_Class_2026', res.data)

        # Verify folder structure on disk
        ws_dir = os.path.join(TestWorkspaceConfig.WORKSPACES_DIR, 'My_Class_2026')
        self.assertTrue(os.path.exists(ws_dir))
        self.assertTrue(os.path.exists(os.path.join(ws_dir, 'workspace.json')))
        self.assertTrue(os.path.exists(os.path.join(ws_dir, 'uploads', 'answer_keys')))
        self.assertTrue(os.path.exists(os.path.join(ws_dir, 'uploads', 'student_submissions')))
        self.assertTrue(os.path.exists(os.path.join(ws_dir, 'results')))
        self.assertTrue(os.path.exists(os.path.join(ws_dir, 'reports')))
        self.assertTrue(os.path.exists(os.path.join(ws_dir, 'exports')))
        self.assertTrue(os.path.exists(os.path.join(ws_dir, 'backups')))

    # 3. Path Traversal & Invalid Workspace Names Rejected
    def test_invalid_workspace_names_and_path_traversal(self):
        self.login()
        invalid_names = ['../hack', '..\\escape', 'invalid/slash', 'test|pipe', '', '   ']
        for bad_name in invalid_names:
            res = self.client.post('/workspaces/create', data={
                'workspace_name': bad_name
            }, follow_redirects=True)
            self.assertIn(b'Invalid workspace name', res.data)

    # 4. Workspace Selection & Switching
    def test_workspace_selection_and_isolation(self):
        self.login()
        self.client.post('/workspaces/create', data={'workspace_name': 'Class_A'}, follow_redirects=True)
        self.client.post('/workspaces/create', data={'workspace_name': 'Class_B'}, follow_redirects=True)

        # Switch to Class_A
        self.client.post('/workspaces/select/Class_A', follow_redirects=True)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('active_workspace'), 'Class_A')

        # Switch to Class_B
        self.client.post('/workspaces/select/Class_B', follow_redirects=True)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('active_workspace'), 'Class_B')

    # 5. Workspace Backup Creation
    def test_workspace_backup(self):
        self.login()
        self.client.post('/workspaces/create', data={'workspace_name': 'Backup_Test_Class'}, follow_redirects=True)
        res = self.client.post('/workspaces/backup/Backup_Test_Class', follow_redirects=True)
        self.assertIn(b'backed up successfully', res.data)

        # Verify ZIP archive exists in backups folder
        backups_dir = os.path.join(TestWorkspaceConfig.WORKSPACES_DIR, 'Backup_Test_Class', 'backups')
        zip_files = [f for f in os.listdir(backups_dir) if f.endswith('.zip')]
        self.assertGreaterEqual(len(zip_files), 1)

    # 6. Database Schema Preservation & Workspace Tagging
    def test_assignment_workspace_tagging(self):
        assign = Assignment(title='Midterm Quiz', workspace_name='Class_A')
        db.session.add(assign)
        db.session.commit()

        queried = Assignment.query.filter_by(workspace_name='Class_A').first()
        self.assertIsNotNone(queried)
        self.assertEqual(queried.title, 'Midterm Quiz')
        self.assertEqual(queried.workspace_name, 'Class_A')

    # 7. Unauthenticated User Cannot Access Workspace Routes
    def test_unauthenticated_workspace_access_blocked(self):
        res = self.client.get('/workspaces/', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/auth/login', res.headers['Location'])

if __name__ == '__main__':
    unittest.main()
