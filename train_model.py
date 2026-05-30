import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def train_model():
    print("Generating synthetic clinical dataset...")
    # Seed for reproducibility
    np.random.seed(42)
    
    # Generate synthetic dataset
    n_samples = 2500
    
    fever = np.random.binomial(1, 0.4, n_samples)
    cough = np.random.binomial(1, 0.5, n_samples)
    sore_throat = np.random.binomial(1, 0.15, n_samples)
    shortness_of_breath = np.random.binomial(1, 0.1, n_samples)
    headache = np.random.binomial(1, 0.2, n_samples)
    age_60_and_above = np.random.binomial(1, 0.25, n_samples)
    gender = np.random.binomial(1, 0.5, n_samples)
    contact = np.random.binomial(1, 0.12, n_samples)
    
    # Probabilistic outcome rules based on actual clinical traits
    # Base risk is low (5%). Having contact with a positive case increases risk significantly (45%).
    # Fever (20%), Shortness of breath (20%), Cough (8%), Sore throat (4%), Headache (3%) are indicators.
    prob = 0.05 + 0.45 * contact + 0.20 * fever + 0.20 * shortness_of_breath + 0.08 * cough + 0.04 * sore_throat + 0.03 * headache + 0.02 * age_60_and_above
    prob = np.clip(prob, 0.01, 0.99)
    
    # Draw binary outcome (0: Negative, 1: Positive)
    covid_status = np.random.binomial(1, prob)
    
    # Create DataFrame
    df = pd.DataFrame({
        'fever': fever,
        'cough': cough,
        'sore_throat': sore_throat,
        'shortness_of_breath': shortness_of_breath,
        'headache': headache,
        'age_60_and_above': age_60_and_above,
        'gender': gender,
        'contact': contact,
        'covid_status': covid_status
    })
    
    X = df.drop('covid_status', axis=1)
    y = df['covid_status']
    
    # Train Random Forest Classifier
    # Limit max_depth to prevent overfitting and guarantee smooth probability scores
    model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=6)
    model.fit(X, y)
    
    acc = model.score(X, y)
    print(f"Model trained successfully. Accuracy on training set: {acc:.4f}")
    
    # Save the model
    with open('covid19Model.pkl', 'wb') as f:
        pickle.dump(model, f)
    print("Saved model to 'covid19Model.pkl'")

if __name__ == '__main__':
    train_model()
