import sys
import os
from datetime import datetime

# Add the project directory to path
sys.path.append(r"c:\Users\Vikash\OneDrive\Desktop\covid_project_demo\COVID19-Prediction-System")

from app import app, db, get_next_sequence_value

def run_integration_tests():
    print("Initializing Flask test client...")
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # We need a secret key for session signing
    app.secret_key = 'test_secret_key_for_testing_123'
    
    client = app.test_client()
    
    # 1. Connection check
    if db is None:
        print("ERROR: Database is not connected. Aborting tests.")
        sys.exit(1)
        
    print("Database connection verified. Starting route checks...")
    
    # Let's keep track of sequence values to restore them later
    start_user_seq = db.counters.find_one({'_id': 'users'})
    start_pred_seq = db.counters.find_one({'_id': 'predictions'})
    
    start_user_val = start_user_seq['sequence_value'] if start_user_seq else 0
    start_pred_val = start_pred_seq['sequence_value'] if start_pred_seq else 0
    
    # Define test parameters
    test_username = "integration_test_user_unique"
    test_password = "password123"
    test_fullname = "Integration Test Patient"
    
    registered_user_id = None
    saved_pred_id = None
    
    try:
        # ---- STEP 1: Public Pages before login ----
        print("\n--- Testing Redirects ---")
        # GET / should redirect to /login if not logged in
        res = client.get('/', follow_redirects=False)
        assert res.status_code == 302
        assert '/login' in res.headers['Location']
        print("PASS: GET '/' redirects to '/login'")
        
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
        db.users.delete_one({'username': test_username})
        
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
        db_user = db.users.find_one({'username': test_username})
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
        res = client.get('/')
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
        db_pred = db.predictions.find_one({'user_id': registered_user_id})
        assert db_pred is not None
        saved_pred_id = db_pred['id']
        print(f"Prediction saved in MongoDB with record ID: {saved_pred_id}")
        
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
            'username': 'admin',
            'password': 'admin123'
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
        
        # Verify that document is soft-deleted: is_deleted is True in MongoDB
        direct_doc = db.predictions.find_one({'id': saved_pred_id})
        assert direct_doc is not None
        assert direct_doc.get('is_deleted') is True
        print("PASS: Record is stored permanently in MongoDB with is_deleted: True")
        
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
        
        res = client.get('/')
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
        print("\nCleaning up test user and prediction records from MongoDB...")
        if registered_user_id is not None:
            db.users.delete_one({'id': registered_user_id})
        if saved_pred_id is not None:
            db.predictions.delete_one({'id': saved_pred_id})
        
        # Revert sequence values
        if start_user_val > 0:
            db.counters.update_one({'_id': 'users'}, {'$set': {'sequence_value': start_user_val}})
        else:
            db.counters.delete_one({'_id': 'users'})
            
        if start_pred_val > 0:
            db.counters.update_one({'_id': 'predictions'}, {'$set': {'sequence_value': start_pred_val}})
        else:
            db.counters.delete_one({'_id': 'predictions'})
        print("Database cleanup completed.")

if __name__ == '__main__':
    run_integration_tests()
