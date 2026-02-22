"""
WearableTest scratch controller — merges gesture classification with Mixxx MIDI output.
Requires: movement_model.pkl (from step2_train_model.py)
"""

import serial
import rtmidi
import numpy as np
import pickle
import time
import threading
from collections import deque

# ─────────────────────────────────────────────────────────────
#  *** CHANGE THESE TO MATCH YOUR SETUP ***
SERIAL_PORT = "/dev/tty.usbserial-1120"
MIDI_PORT_NAME = "WearableTest"
MODEL_FILE = "movement_model.pkl"
# ─────────────────────────────────────────────────────────────

BAUD               = 115200
CONFIDENCE_SCRATCH = 45   # left/right — slightly more lenient
CONFIDENCE_VOL    = 50   # up/down — stricter
CONFIRM_COUNT      = 5
SILENCE_LIMIT      = 10

VOL_CC        = 7
JOG_CC        = 16
SCRATCH_NOTE  = 60
MIDI_CH       = 0

VOL_STEP      = 3
JOG_TICK      = 6
JOG_INTERVAL  = 0.05

# ── Load model ──
print("=" * 50)
print("WearableTest: Gesture → Mixxx Controller")
print("=" * 50)

try:
    with open(MODEL_FILE, "rb") as f:
        bundle = pickle.load(f)
    clf         = bundle["model"]
    classes     = bundle["classes"]
    WINDOW_SIZE = bundle["window_size"]
    STEP_SIZE   = bundle["step_size"]
    print(f"✅ Model loaded. Detects: {classes}")
except FileNotFoundError:
    print(f"\nERROR: '{MODEL_FILE}' not found. Run step2_train_model.py first.")
    exit()

# ── Connect to MIDI ──
midi = rtmidi.MidiOut()
ports = midi.get_ports()
port_index = next((i for i, name in enumerate(ports) if MIDI_PORT_NAME in name), None)
if port_index is None:
    raise RuntimeError(f"Could not find MIDI port '{MIDI_PORT_NAME}'. Available: {ports}")
midi.open_port(port_index)
print(f"✅ MIDI connected: {ports[port_index]}")

# ── Connect to Arduino ──
print(f"\nConnecting to Arduino on {SERIAL_PORT}...")
try:
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
    time.sleep(2)
    ser.flushInput()
    print("✅ Arduino connected!\n")
except Exception as e:
    print(f"\nERROR: Could not connect to {SERIAL_PORT}\n  {e}")
    exit()

# ── MIDI helpers ──
volume = 80
jog_direction = 0
jog_thread = None
jog_lock = threading.Lock()

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def send_cc(cc, value):
    midi.send_message([0xB0 + MIDI_CH, cc & 0x7F, value & 0x7F])

def send_note_on():
    midi.send_message([0x90 + MIDI_CH, SCRATCH_NOTE & 0x7F, 127])

def send_note_off():
    midi.send_message([0x80 + MIDI_CH, SCRATCH_NOTE & 0x7F, 0])

def jog_loop():
    global jog_direction
    while True:
        with jog_lock:
            d = jog_direction
        if d == 0:
            break
        val = clamp(64 + JOG_TICK * d, 1, 127)
        send_cc(JOG_CC, val)
        threading.Event().wait(JOG_INTERVAL)

def start_jog(direction):
    global jog_direction, jog_thread
    with jog_lock:
        already_running = jog_direction != 0
        jog_direction = direction
    if not already_running:
        send_note_on()
        jog_thread = threading.Thread(target=jog_loop, daemon=True)
        jog_thread.start()

def stop_jog():
    global jog_direction
    with jog_lock:
        jog_direction = 0
    send_note_off()

# ── Gesture → action ──
def handle_gesture(label):
    global volume
    if label == "LEFT":
        start_jog(-1)
    elif label == "RIGHT":
        start_jog(+1)
    elif label in ("REST", "NONE"):
        stop_jog()
    elif label == "UP":
        volume = clamp(volume + VOL_STEP, 0, 127)
        send_cc(VOL_CC, volume)
        print(f"  VOL {volume}")
    elif label == "DOWN":
        volume = clamp(volume - VOL_STEP, 0, 127)
        send_cc(VOL_CC, volume)
        print(f"  VOL {volume}")

# ── Feature extraction ──
def extract_features(window):
    features = []
    for col in range(window.shape[1]):
        vals = window[:, col]
        features += [vals.mean(), vals.std(), vals.min(), vals.max(), vals.max() - vals.min()]
    return features

# ── Live loop ──
buffer         = deque(maxlen=WINDOW_SIZE)
sample_count   = 0
last_label     = None
confirm_buffer = deque(maxlen=CONFIRM_COUNT)
silence_count  = 0

print("─" * 40)
print("Move the sensor to control Mixxx!")
print("  LEFT / RIGHT  →  scratch")
print("  UP / DOWN     →  volume")
print("  REST          →  resume playback")
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

                threshold = CONFIDENCE_SCRATCH if pred in ("LEFT", "RIGHT") else CONFIDENCE_VOL

                if conf >= threshold:
                    silence_count = 0
                    confirm_buffer.append(pred)
                else:
                    silence_count += 1
                    confirm_buffer.append(None)
                    if silence_count >= SILENCE_LIMIT:
                        if last_label not in (None, "REST", "NONE"):
                            print("  (no confident gesture — stopping)")
                            stop_jog()
                            last_label = "REST"
                        silence_count = 0

                if (len(confirm_buffer) == CONFIRM_COUNT
                        and len(set(confirm_buffer)) == 1
                        and confirm_buffer[-1] is not None
                        and conf >= threshold
                        and pred != last_label):
                    print(f"  {pred}  ({conf:.0f}%)")
                    handle_gesture(pred)
                    last_label = pred

            except Exception as e:
                print(f"Prediction error: {e}")
                break

except KeyboardInterrupt:
    print("\n\nStopped.")
finally:
    stop_jog()
    ser.close()