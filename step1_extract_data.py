"""
STEP 1 — Extract your data from all PDFs and save as a CSV file.

How to run:
  1. Put ALL your PDF files in the same folder as this script
  2. Open a terminal/command prompt in that folder
  3. Run:  pip install pdfplumber pandas
  4. Run:  python step1_extract_data.py

This will create a file called:  gesture_data.csv
"""

import pdfplumber
import pandas as pd
import os

PDF_FILES = [
    "rest.pdf",
    "up.pdf",
    "down.pdf",
    "fwd.pdf",
    "bwd.pdf",
    "left.pdf",
    "right.pdf",
]
CSV_FILE = "gesture_data.csv"

print("=" * 50)
print("STEP 1: Extracting data from PDFs...")
print("=" * 50)

rows = []
for PDF_FILE in PDF_FILES:
    if not os.path.exists(PDF_FILE):
        print(f"WARNING: Could not find '{PDF_FILE}' — skipping.")
        continue

    with pdfplumber.open(PDF_FILE) as pdf:
        print(f"Reading '{PDF_FILE}' ({len(pdf.pages)} pages)...")
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split('\n'):
                parts = line.strip().split(',')
                if len(parts) == 7:
                    try:
                        float(parts[0])
                        label = parts[1].strip()
                        if label == 'UPDOWN':
                            continue  # Skip old combined label
                        rows.append(parts)
                    except ValueError:
                        pass

print(f"\nExtracted {len(rows)} total data rows.")

df = pd.DataFrame(rows, columns=["timestamp", "label", "accelX", "accelY", "accelZ", "gyroX", "gyroY"])
df = df.astype({
    "timestamp": float,
    "accelX": float, "accelY": float, "accelZ": float,
    "gyroX": float, "gyroY": float
})

df.to_csv(CSV_FILE, index=False)

print(f"\n✅ Saved to '{CSV_FILE}'")
print("\nSamples per movement:")
print(df["label"].value_counts().to_string())
print("\nDone! Now run:  python step2_train_model.py")
