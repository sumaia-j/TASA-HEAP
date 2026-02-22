"""
STEP 3 — Live movement detection from your Arduino.

How to run:
  1. Make sure you ran step2_train_model.py and have movement_model.pkl
  2. Plug in your Arduino with your sketch uploaded
  3. Close Arduino IDE completely
  4. Change PORT below to match your Arduino's port
  5. Run:  python step3_live_classify.py
"""

import serial
import numpy as np
import pickle
import time
from collections import deque

# ─────────────────────────────────────────────────────────────
#  *** CHANGE THIS TO YOUR ARDUINO'S PORT ***
PORT = "COM4"
# ─────────────────────────────────────────────────────────────

BAUD            = 115200
MODEL_FILE      = "movement_model.pkl"
CONFIDENCE      = 50    # Only report if above 50% confident
CONFIRM_COUNT   = 6     # Must see same label this many times in a row

DISPLAY = {
    "REST":  "RESTING",
    "UP":    "UP",
    "DOWN":  "DOWN",
    "FWD":   "FORWARD",
    "BWD":   "BACKWARD",
    "LEFT":  "LEFT",
    "RIGHT": "RIGHT",
}

print("=" * 50)
print("STEP 3: Live Movement Detection")
print("=" * 50)

# ── Load model ──
try:
    with open(MODEL_FILE, "rb") as f:
        bundle = pickle.load(f)
    clf         = bundle["model"]
    classes     = bundle["classes"]
    WINDOW_SIZE = bundle["window_size"]
    STEP_SIZE   = bundle["step_size"]
    n_features  = bundle.get("n_features", "unknown")
    print(f"✅ Model loaded. Can detect: {classes}")
    print(f"✅ Expects {n_features} features per window")
except FileNotFoundError:
    print(f"\nERROR: '{MODEL_FILE}' not found.")
    print("Run step2_train_model.py first.")
    exit()

# ── Connect to Arduino ──
print(f"\nConnecting to Arduino on {PORT}...")
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    ser.flushInput()
    print("✅ Connected!\n")
except Exception as e:
    print(f"\nERROR: Could not connect to {PORT}")
    print(f"  {e}")
    print("\nFix: Close Arduino IDE fully, then try again.")
    exit()

# ── Feature extraction — must match step2 exactly ──
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

# ── Live loop ──
buffer          = deque(maxlen=WINDOW_SIZE)
sample_count    = 0
last_label      = None
confirm_buffer  = deque(maxlen=CONFIRM_COUNT)

print("─" * 40)
print("Move the sensor to see results!")
print("Press Ctrl+C to stop.")
print("─" * 40 + "\n")

try:
    while True:
        try:
            raw = ser.readline().decode("utf-8", errors="ignore").strip()
        except Exception:
            continue

        if not raw or raw.startswith("#") or raw.startswith("t_ms"):
            continue

        parts = raw.split(",")

        if len(parts) != 7:
            continue

        try:
            sample = [float(parts[2]), float(parts[3]), float(parts[4]),
                      float(parts[5]), float(parts[6])]
        except ValueError:
            continue

        buffer.append(sample)
        sample_count += 1

        if len(buffer) == WINDOW_SIZE and sample_count % STEP_SIZE == 0:
            window = np.array(buffer)
            feats  = np.array([extract_features(window)])

            try:
                pred  = clf.predict(feats)[0]
                proba = clf.predict_proba(feats)[0]
                conf  = max(proba) * 100

                # Only add to confirm buffer if confidence is high enough
                if conf >= CONFIDENCE:
                    confirm_buffer.append(pred)
                else:
                    confirm_buffer.append(None)

                # Only print if all recent predictions agree on the same label
                # and the current confidence still meets the threshold
                if (len(confirm_buffer) == CONFIRM_COUNT
                        and len(set(confirm_buffer)) == 1
                        and confirm_buffer[-1] is not None
                        and conf >= CONFIDENCE
                        and pred != last_label):
                    label_text = DISPLAY.get(pred, pred)
                    print(f"  {label_text}   ({conf:.0f}% confident)")
                    last_label = pred

            except Exception as e:
                print(f"Prediction error: {e}")
                break

except KeyboardInterrupt:
    print("\n\nStopped. Goodbye!")
finally:
    ser.close()
