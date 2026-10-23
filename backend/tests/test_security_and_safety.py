import unittest
import os
import io
from app import create_app, db
from app.models import User, Assignment, Rubric
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key-for-unit-testing'
    MAX_CONTENT_LENGTH = 1024 * 1024 # 1MB limit for testing

class SecurityAndSafetyTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed test admin user
        self.user = User(username='testadmin', email='testadmin@example.com')
        self.user.set_password('CorrectPassword123!')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self, username, password):
        return self.client.post('/auth/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/auth/logout', follow_redirects=True)

    # Test 1: Authentication and Session Handling
    def test_authentication_success_and_failure(self):
        # Invalid credentials
        res = self.login('testadmin', 'WrongPassword')
        self.assertIn(b'Invalid username or password', res.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('user_id'))

        # Valid credentials
        res = self.login('testadmin', 'CorrectPassword123!')
        self.assertIn(b'Welcome back, testadmin!', res.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('user_id'), self.user.id)
            self.assertEqual(sess.get('username'), 'testadmin')

        # Logout
        res = self.logout()
        self.assertIn(b'You have been logged out', res.data)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get('user_id'))

    # Test 2: Unauthenticated Access to Protected Routes is Blocked
    def test_protected_routes_redirect_unauthenticated_users(self):
        protected_urls = [
            '/grading/evaluate',
            '/rubrics/generate',
            '/grading/report/1',
            '/grading/report/1/download',
            '/grading/report/1/csv',
            '/grading/report/1/student/1/pdf'
        ]
        for url in protected_urls:
            res = self.client.get(url, follow_redirects=False)
            self.assertEqual(res.status_code, 302, f"Expected 302 redirect for unauthenticated access to {url}")
            self.assertIn('/auth/login', res.headers['Location'])

    # Test 3: Authenticated User Can Access Protected Routes
    def test_authenticated_access_to_evaluate_and_rubrics(self):
        self.login('testadmin', 'CorrectPassword123!')
        res_eval = self.client.get('/grading/evaluate')
        self.assertEqual(res_eval.status_code, 200)
        self.assertIn(b'Bulk Assignment Evaluator', res_eval.data)

        res_rubric = self.client.get('/rubrics/generate')
        self.assertEqual(res_rubric.status_code, 200)
        self.assertIn(b'Generate Rubric', res_rubric.data)

    # Test 4: File Validation (Rejects Non-PDF Files)
    def test_upload_rejects_non_pdf_files(self):
        self.login('testadmin', 'CorrectPassword123!')
        data = {
            'assignment_title': 'Test Assignment',
            'teacher_pdf': (io.BytesIO(b"fake text file"), 'rubric.txt'),
            'student_pdfs': [(io.BytesIO(b"student text"), 'student.txt')]
        }
        res = self.client.post('/grading/evaluate', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertIn(b'Invalid Teacher Rubric file. Only valid .pdf files are accepted', res.data)

    # Test 5: Production SECRET_KEY Enforcement
    def test_production_secret_key_required(self):
        class ProductionNoKeyConfig(Config):
            ENV = 'production'
            SECRET_KEY = None

        with self.assertRaises(ValueError) as ctx:
            create_app(ProductionNoKeyConfig)
        self.assertIn('SECRET_KEY must be configured in production environment', str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
