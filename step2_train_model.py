"""
STEP 2 — Train the movement detection model from your CSV data.

How to run:
  1. Make sure you ran step1_extract_data.py and have gesture_data.csv
  2. Run:  python step2_train_model.py

This will create a file called:  movement_model.pkl
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pickle
import os

CSV_FILE    = "gesture_data.csv"
MODEL_FILE  = "movement_model.pkl"
WINDOW_SIZE = 30
STEP_SIZE   = 5
FEATURE_COLS = ["accelX", "accelY", "accelZ", "gyroX", "gyroY"]

print("=" * 50)
print("STEP 2: Training movement model...")
print("=" * 50)

# Delete old model if it exists
if os.path.exists(MODEL_FILE):
    os.remove(MODEL_FILE)
    print("Deleted old model.")

try:
    df = pd.read_csv(CSV_FILE)
except FileNotFoundError:
    print(f"\nERROR: '{CSV_FILE}' not found.")
    print("Run step1_extract_data.py first.")
    exit()

print(f"\nLoaded {len(df)} rows.")
print("\nSamples per movement:")
print(df["label"].value_counts().to_string())

def extract_features(window):
    features = []
    for col in range(window.shape[1]):
        vals = window[:, col]
        features += [
            vals.mean(),
            vals.std(),
            vals.min(),
            vals.max(),
            vals.max() - vals.min(),
        ]
    return features

X, y = [], []
for label, group in df.groupby("label"):
    data = group[FEATURE_COLS].values
    for start in range(0, len(data) - WINDOW_SIZE + 1, STEP_SIZE):
        window = data[start:start + WINDOW_SIZE]
        X.append(extract_features(window))
        y.append(label)

X, y = np.array(X), np.array(y)
print(f"\nCreated {len(X)} windows across {len(set(y))} classes")
print(f"Features per window: {X.shape[1]}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

clf = RandomForestClassifier(
    n_estimators=300,
    max_depth=20,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)
clf.fit(X_train, y_train)

y_pred = clf.predict(X_test)
print("\n--- Results ---")
print(classification_report(y_test, y_pred))

with open(MODEL_FILE, "wb") as f:
    pickle.dump({
        "model": clf,
        "classes": list(clf.classes_),
        "window_size": WINDOW_SIZE,
        "step_size": STEP_SIZE,
        "feature_cols": FEATURE_COLS,
        "n_features": X.shape[1]
    }, f)

print(f"✅ Model saved to '{MODEL_FILE}'")
print(f"✅ Features: {X.shape[1]}")
print("\nDone! Now run:  python step3_live_classify.py")
