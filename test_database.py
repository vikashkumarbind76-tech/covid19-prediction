import sys
import os
import sqlite3

# Add the project directory to path so we can import from app.py
sys.path.append(r"c:\Users\Vikash\OneDrive\Desktop\covid_project_demo\COVID19-Prediction-System")

from app import (
    is_db_connected,
    db_get_user_by_username,
    db_get_user_by_id,
    db_create_user,
    get_next_sequence_value,
    db_create_prediction,
    db_get_prediction_by_id,
    db_get_predictions_by_user_id,
    db_get_all_predictions,
    db_get_users_map,
    db_delete_prediction,
    DB_PATH
)

def test_database():
    print("Testing SQLite database operations...")
    
    # 1. Check connection
    connected = is_db_connected()
    print(f"Database connected: {connected}")
    assert connected, "Database connection check failed"
    
    # 2. Get next sequence values
    user_seq = get_next_sequence_value('users')
    pred_seq = get_next_sequence_value('predictions')
    print(f"Next sequence for 'users': {user_seq}")
    print(f"Next sequence for 'predictions': {pred_seq}")
    
    # 3. Create a test user
    # Clean up any leftover test data for this ID from previous failed runs/crashes
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_seq,))
    cursor.execute("DELETE FROM predictions WHERE user_id = ?", (user_seq,))
    conn.commit()
    conn.close()

    test_username = f"temp_user_{user_seq}"
    test_user_data = {
        'id': user_seq,
        'username': test_username,
        'password': 'hashed_test_password',
        'name': 'Testy McTestface',
        'age': 45,
        'gender': 'Male',
        'created_at': '2026-05-31 12:00:00'
    }
    print(f"Creating user {test_username}...")
    db_create_user(user_seq, test_user_data)
    
    # 4. Fetch the user back
    fetched_by_username = db_get_user_by_username(test_username)
    print("Fetched by username:", fetched_by_username)
    assert fetched_by_username is not None
    assert fetched_by_username['name'] == 'Testy McTestface'
    
    fetched_by_id = db_get_user_by_id(user_seq)
    print("Fetched by ID:", fetched_by_id)
    assert fetched_by_id is not None
    assert fetched_by_id['username'] == test_username
    
    # 5. Create a prediction
    test_pred_data = {
        'id': pred_seq,
        'name': 'Test Patient',
        'age': 45,
        'gender': 'Male',
        'fever': 1,
        'cough': 0,
        'sore_throat': 1,
        'shortness_of_breath': 0,
        'headache': 0,
        'age_60_and_above': 0,
        'contact': 1,
        'prediction_result': 'Negative',
        'prediction_probability': 0.15,
        'timestamp': '2026-05-31 12:05:00',
        'user_id': user_seq
    }
    print(f"Creating prediction record with ID {pred_seq}...")
    db_create_prediction(pred_seq, test_pred_data)
    
    # 6. Retrieve prediction
    fetched_pred = db_get_prediction_by_id(pred_seq)
    print("Fetched prediction:", fetched_pred)
    assert fetched_pred is not None
    assert fetched_pred['name'] == 'Test Patient'
    
    # 7. Retrieve predictions by user ID
    user_preds = db_get_predictions_by_user_id(user_seq)
    print(f"Predictions for user ID {user_seq}:", user_preds)
    assert len(user_preds) == 1
    assert user_preds[0]['id'] == pred_seq
    
    # 8. Get all predictions
    all_preds = db_get_all_predictions()
    print("Total predictions count:", len(all_preds))
    assert len(all_preds) >= 1
    
    # 9. Get users map
    users_map = db_get_users_map()
    print("Users map key count:", len(users_map))
    assert user_seq in users_map
    assert users_map[user_seq] == test_username
    
    # 10. Test soft delete and direct database state
    print(f"Deleting prediction ID {pred_seq}...")
    db_delete_prediction(pred_seq)
    
    # Verify it is omitted from app queries
    deleted_pred = db_get_prediction_by_id(pred_seq)
    print("Fetched active prediction after soft delete (should be None):", deleted_pred)
    assert deleted_pred is None
    
    # Verify it still exists in raw database with is_deleted=1 (soft delete verification)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM predictions WHERE id = ?", (pred_seq,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None, "Record was permanently deleted, but should be soft deleted"
    row_dict = dict(row)
    assert row_dict['is_deleted'] == 1, f"is_deleted flag should be 1, found {row_dict['is_deleted']}"
    print("Soft delete verified successfully in SQLite database!")
    
    # Clean up user and prediction from database manually (so we don't pollute the test database)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_seq,))
    cursor.execute("DELETE FROM predictions WHERE id = ?", (pred_seq,))
    # Also revert sequences back in sqlite_sequence
    cursor.execute("UPDATE sqlite_sequence SET seq = seq - 1 WHERE name = 'users'")
    cursor.execute("UPDATE sqlite_sequence SET seq = seq - 1 WHERE name = 'predictions'")
    conn.commit()
    conn.close()
    
    print("\nAll database operations completed successfully!")

if __name__ == '__main__':
    test_database()
