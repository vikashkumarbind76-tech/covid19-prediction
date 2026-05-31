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
    db_delete_prediction,
    db  # MongoDB database reference from app.py
)

def test_mongo_soft_delete():
    print("Testing MongoDB setup & Soft Delete capabilities...")
    
    # 1. Connection check
    connected = is_db_connected()
    print(f"Database connected: {connected}")
    assert connected, "MongoDB is not connected"
    
    # 2. Sequence values
    user_seq = get_next_sequence_value('users')
    pred_seq = get_next_sequence_value('predictions')
    print(f"Next sequence for 'users': {user_seq}")
    print(f"Next sequence for 'predictions': {pred_seq}")
    
    # 3. Create user
    test_username = f"mongo_user_{user_seq}"
    test_user_data = {
        'id': user_seq,
        'username': test_username,
        'password': 'hashed_test_password',
        'name': 'Mongo Tester',
        'age': 32,
        'gender': 'Female',
        'created_at': '2026-05-31 12:00:00'
    }
    print(f"Creating user '{test_username}'...")
    db_create_user(user_seq, test_user_data)
    
    # 4. Fetch user
    fetched_user = db_get_user_by_username(test_username)
    print("Fetched user:", fetched_user)
    assert fetched_user is not None
    assert fetched_user['name'] == 'Mongo Tester'
    
    # 5. Create prediction
    test_pred_data = {
        'id': pred_seq,
        'name': 'Mongo Patient',
        'age': 32,
        'gender': 'Female',
        'fever': 0,
        'cough': 1,
        'sore_throat': 0,
        'shortness_of_breath': 0,
        'headache': 1,
        'age_60_and_above': 0,
        'contact': 0,
        'prediction_result': 'Negative',
        'prediction_probability': 0.08,
        'timestamp': '2026-05-31 12:10:00',
        'user_id': user_seq
    }
    print(f"Creating prediction record with ID {pred_seq}...")
    db_create_prediction(pred_seq, test_pred_data)
    
    # 6. Retrieve active prediction
    fetched_pred = db_get_prediction_by_id(pred_seq)
    print("Fetched prediction:", fetched_pred)
    assert fetched_pred is not None
    assert fetched_pred['name'] == 'Mongo Patient'
    
    # 7. Perform soft delete
    print(f"Soft-deleting prediction ID {pred_seq}...")
    db_delete_prediction(pred_seq)
    
    # 8. Verify it is hidden from helper queries (deleted check)
    hidden_pred = db_get_prediction_by_id(pred_seq)
    print("Fetched active prediction after soft delete (should be None):", hidden_pred)
    assert hidden_pred is None, "Soft deleted record was found in active query!"
    
    user_preds = db_get_predictions_by_user_id(user_seq)
    print(f"Predictions for user ID {user_seq} after soft delete (should be empty):", user_preds)
    assert len(user_preds) == 0, "Soft deleted record appeared in user predictions list!"
    
    # 9. Verify it STILL exists permanently in MongoDB collection
    mongo_doc = db.predictions.find_one({'id': pred_seq})
    print("Direct MongoDB query output (should exist):", mongo_doc)
    assert mongo_doc is not None, "Data was deleted permanently! It should have been kept in MongoDB."
    assert mongo_doc['is_deleted'] is True, "is_deleted flag was not set to True!"
    print("Confirmation: Data is stored permanently in MongoDB with 'is_deleted': True!")
    
    # 10. Clean up test documents completely from database
    print("Cleaning up database test documents...")
    db.users.delete_one({'id': user_seq})
    db.predictions.delete_one({'id': pred_seq})
    
    # Revert sequence values in counters collection
    db.counters.update_one({'_id': 'users'}, {'$inc': {'sequence_value': -1}})
    db.counters.update_one({'_id': 'predictions'}, {'$inc': {'sequence_value': -1}})
    
    print("\nAll MongoDB soft-delete tests passed successfully!")

if __name__ == '__main__':
    test_mongo_soft_delete()
