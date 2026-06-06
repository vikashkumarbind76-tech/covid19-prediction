import sys
import os
from datetime import datetime

# Add the project directory to path
sys.path.append(r"c:\Users\Vikash\OneDrive\Desktop\covid_project_demo\COVID19-Prediction-System")

# Set test environment variables before importing app
os.environ['ADMIN_USERNAME'] = 'test_admin_user'
os.environ['ADMIN_PASSWORD'] = 'test_admin_password_123'

from app import app, get_next_sequence_value, DB_PATH, ADMIN_USERNAME, ADMIN_PASSWORD
import sqlite3

def run_integration_tests():
    print("Initializing Flask test client...")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # We need a secret key for session signing
    app.secret_key = 'test_secret_key_for_testing_123'
    
    client = app.test_client()
    
    # 1. Connection check
    from app import is_db_connected
    if not is_db_connected():
        print("ERROR: Database is not connected. Aborting tests.")
        sys.exit(1)
        
    print("Database connection verified. Starting route checks...")
    
    # Let's keep track of sequence values to restore them later
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT seq FROM sqlite_sequence WHERE name = 'users'")
    row_user = cursor.fetchone()
    cursor.execute("SELECT seq FROM sqlite_sequence WHERE name = 'predictions'")
    row_pred = cursor.fetchone()
    conn.close()
    
    start_user_val = row_user[0] if row_user else 0
    start_pred_val = row_pred[0] if row_pred else 0
    
    # Define test parameters
    test_username = "integration_test_user_unique"
    test_password = "password123"
    test_fullname = "Integration Test Patient"
    
    registered_user_id = None
    saved_pred_id = None
    
    try:
        # ---- STEP 1: Public Pages before login ----
        print("\n--- Testing Redirects ---")
        # GET / should load the public homepage
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 200
        assert b"COVID-19" in res.data or b"Diagnostics" in res.data
        print("PASS: GET '/' loads public homepage successfully")
        
        # GET /dashboard should redirect to /login if not logged in
        res = client.get('/dashboard', follow_redirects=False)
        assert res.status_code == 302
        assert '/login' in res.headers['Location']
        print("PASS: GET '/dashboard' redirects to '/login' when not logged in")
        
        # ---- STEP 2: Login and Registration Pages Load ----
        print("\n--- Testing Page Loads ---")
        res = client.get('/login')
        assert res.status_code == 200
        assert b"Log In" in res.data or b"Login" in res.data
        print("PASS: GET '/login' loads page")
        
        res = client.get('/register')
        assert res.status_code == 200
        assert b"Create Account" in res.data or b"Register" in res.data
        print("PASS: GET '/register' loads page")
        
        # ---- STEP 3: User Registration ----
        print("\n--- Testing User Registration ---")
        # Clean up in case duplicate user exists from a previous crash
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (test_username,))
        conn.commit()
        conn.close()
        
        res = client.post('/register', data={
            'username': test_username,
            'password': test_password,
            'name': test_fullname,
            'age': '28',
            'gender': 'Male'
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Registration successful" in res.data or b"Log In" in res.data or b"Login" in res.data
        
        # Verify user is inserted in DB
        from app import db_get_user_by_username
        db_user = db_get_user_by_username(test_username)
        assert db_user is not None
        registered_user_id = db_user['id']
        assert db_user['name'] == test_fullname
        print(f"PASS: POST '/register' successfully created user '{test_username}' with ID {registered_user_id}")
        
        # ---- STEP 4: Duplicate Registration Check ----
        res = client.post('/register', data={
            'username': test_username,
            'password': test_password,
            'name': test_fullname,
            'age': '28',
            'gender': 'Male'
        }, follow_redirects=True)
        assert b"Username already registered" in res.data
        print("PASS: Registration handles duplicate username correctly")
        
        # ---- STEP 5: User Login ----
        print("\n--- Testing User Login ---")
        # Login with wrong credentials
        res = client.post('/login', data={
            'username': test_username,
            'password': 'wrongpassword'
        }, follow_redirects=True)
        assert b"Invalid username or password" in res.data
        print("PASS: Login rejects incorrect password")
        
        # Login with correct credentials
        res = client.post('/login', data={
            'username': test_username,
            'password': test_password
        }, follow_redirects=True)
        assert res.status_code == 200
        print("PASS: Login accepts correct credentials and enters portal")
        
        # ---- STEP 6: User Dashboard (Loads 0 records initially) ----
        print("\n--- Testing Dashboard Load ---")
        res = client.get('/dashboard')
        assert res.status_code == 200
        # Check that totals are rendered on dashboard
        assert b"Total" in res.data or b"0" in res.data
        print("PASS: User Dashboard loaded successfully")
        
        # ---- STEP 7: Screening Form Page ----
        print("\n--- Testing Screening Page ---")
        res = client.get('/screen')
        assert res.status_code == 200
        assert b"COVID-19 Risk Screening" in res.data or b"Symptom" in res.data or b"Submit" in res.data
        print("PASS: Screening form page loaded")
        
        # ---- STEP 8: Prediction API ----
        print("\n--- Testing Prediction API ---")
        # Send symptom checklist
        res = client.post('/predict', json={
            'name': test_fullname,
            'age': 28,
            'gender': 'Male',
            'fever': True,
            'cough': True,
            'sore_throat': False,
            'shortness_of_breath': False,
            'headache': True,
            'contact': True
        })
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data['success'] is True
        assert 'result' in json_data
        assert 'probability' in json_data
        assert 'recommendations' in json_data
        print(f"PASS: POST '/predict' returned result={json_data['result']}, prob={json_data['probability']}%")
        
        # Verify prediction document was stored in DB
        from app import db_get_predictions_by_user_id
        user_preds = db_get_predictions_by_user_id(registered_user_id)
        assert len(user_preds) > 0
        db_pred = user_preds[0]
        saved_pred_id = db_pred['id']
        print(f"Prediction saved in SQLite database with record ID: {saved_pred_id}")
        
        # ---- STEP 9: Report Generation (Word DOCX) ----
        print("\n--- Testing DOCX Report Generation ---")
        res = client.get(f'/download/docx/{saved_pred_id}')
        assert res.status_code == 200
        assert res.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        print("PASS: GET '/download/docx/<id>' downloads DOCX file")
        
        # ---- STEP 10: Report Generation (PDF) ----
        print("\n--- Testing PDF Report Generation ---")
        res = client.get(f'/download/pdf/{saved_pred_id}')
        assert res.status_code == 200
        assert res.headers['Content-Type'] == 'application/pdf'
        print("PASS: GET '/download/pdf/<id>' downloads PDF file")
        
        # ---- STEP 11: Admin Authentication Flow ----
        print("\n--- Testing Admin Panel ---")
        # GET admin login
        res = client.get('/admin/login')
        assert res.status_code == 200
        assert b"Admin Login" in res.data or b"username" in res.data
        
        # POST admin login (wrong credentials)
        res = client.post('/admin/login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        assert b"Invalid credentials" in res.data
        print("PASS: Admin login rejects wrong credentials")
        
        # POST admin login (correct credentials)
        res = client.post('/admin/login', data={
            'username': ADMIN_USERNAME,
            'password': ADMIN_PASSWORD
        }, follow_redirects=True)
        assert res.status_code == 200
        print("PASS: Admin login succeeds and enters dashboard")
        
        # ---- STEP 12: Admin Dashboard Page ----
        res = client.get('/admin/dashboard')
        assert res.status_code == 200
        assert b"Total Screenings" in res.data
        # Page should show our newly registered user's record
        assert test_fullname.encode('utf-8') in res.data
        print("PASS: Admin Dashboard loads stats and tables successfully")
        
        # ---- STEP 13: Admin CSV Export ----
        res = client.get('/admin/export')
        assert res.status_code == 200
        print("CSV Export Headers:", dict(res.headers))
        content_type = res.headers.get('Content-Type', '')
        assert 'text/csv' in content_type or 'vnd.ms-excel' in content_type
        print("PASS: Admin CSV export downloaded successfully")
        
        # ---- STEP 14: Admin Deletes Record (Soft Delete Verification) ----
        print("\n--- Testing Admin Soft Delete ---")
        res = client.post(f'/admin/delete/{saved_pred_id}', follow_redirects=True)
        assert res.status_code == 200
        json_res = res.get_json()
        assert json_res['success'] is True
        print("PASS: POST '/admin/delete/<id>' returned success JSON")
        
        # Verify that document is soft-deleted: is_deleted is 1 in SQLite
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM predictions WHERE id = ?", (saved_pred_id,))
        direct_doc_row = cursor.fetchone()
        conn.close()
        assert direct_doc_row is not None
        direct_doc = dict(direct_doc_row)
        assert direct_doc.get('is_deleted') == 1
        print("PASS: Record is stored permanently in SQLite database with is_deleted: 1")
        
        # Verify it is omitted from the Admin Dashboard view
        res = client.get('/admin/dashboard')
        assert f"/download/pdf/{saved_pred_id}".encode('utf-8') not in res.data
        assert f"/download/docx/{saved_pred_id}".encode('utf-8') not in res.data
        print("PASS: Deleted record is successfully filtered out from Admin Dashboard UI")
        
        # Verify it is omitted from User Dashboard view
        # We need to log user back in (since admin dashboard session overwrites or we are in same client session)
        client.post('/login', data={
            'username': test_username,
            'password': test_password
        }, follow_redirects=True)
        
        res = client.get('/dashboard')
        assert f"/download/pdf/{saved_pred_id}".encode('utf-8') not in res.data
        assert f"/download/docx/{saved_pred_id}".encode('utf-8') not in res.data
        print("PASS: Deleted record is successfully filtered out from User Dashboard UI")
        
        # ---- STEP 15: Logouts ----
        print("\n--- Testing Logouts ---")
        res = client.get('/logout', follow_redirects=True)
        assert b"Log In" in res.data or b"Login" in res.data or res.status_code == 200
        print("PASS: User logout successfully redirects")
        
        res = client.get('/admin/logout', follow_redirects=True)
        assert b"Admin Login" in res.data or b"Login" in res.data or res.status_code == 200
        print("PASS: Admin logout successfully redirects")
        
        print("\n==========================================")
        print("ALL APP INTEGRATION TESTS PASSED SUCCESSFULLY!")
        print("==========================================")
        
    except AssertionError as e:
        print(f"\nAssertion Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up database test documents entirely
        print("\nCleaning up test user and prediction records from SQLite...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if registered_user_id is not None:
            cursor.execute("DELETE FROM users WHERE id = ?", (registered_user_id,))
        if saved_pred_id is not None:
            cursor.execute("DELETE FROM predictions WHERE id = ?", (saved_pred_id,))
        
        # Revert sequence values
        if start_user_val > 0:
            cursor.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'users'", (start_user_val,))
        else:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'users'")
            
        if start_pred_val > 0:
            cursor.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'predictions'", (start_pred_val,))
        else:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'predictions'")
        conn.commit()
        conn.close()
        print("Database cleanup completed.")

if __name__ == '__main__':
    run_integration_tests()
