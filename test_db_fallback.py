import sys
import os

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
    db_delete_prediction
)

def test_database():
    print("Testing Database dual-mode setup (should fall back to SQLite when Firebase is not configured)...")
    
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
    import sqlite3
    conn = sqlite3.connect(os.path.join(r"c:\Users\Vikash\OneDrive\Desktop\covid_project_demo\COVID19-Prediction-System", 'database', 'predictions.db'))
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
    
    # 10. Clean up / Delete prediction
    print(f"Deleting prediction ID {pred_seq}...")
    db_delete_prediction(pred_seq)
    deleted_pred = db_get_prediction_by_id(pred_seq)
    print("Fetched deleted prediction:", deleted_pred)
    assert deleted_pred is None
    
    # Clean up user from database manually (so we don't pollute the test database)
    import sqlite3
    conn = sqlite3.connect(os.path.join(r"c:\Users\Vikash\OneDrive\Desktop\covid_project_demo\COVID19-Prediction-System", 'database', 'predictions.db'))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_seq,))
    # Also revert sequences back in sqlite_sequence
    cursor.execute("UPDATE sqlite_sequence SET seq = seq - 1 WHERE name = 'users'")
    cursor.execute("UPDATE sqlite_sequence SET seq = seq - 1 WHERE name = 'predictions'")
    conn.commit()
    conn.close()
    
    print("\nAll database operations completed successfully!")

if __name__ == '__main__':
    test_database()
