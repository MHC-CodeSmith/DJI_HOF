#!/usr/bin/env python3
"""
sync_video_csv.py

1) Loads the trained Pixelwise model (SGDClassifier).
2) Opens the flight video.
3) Reads the metadata CSV (with timestamps/frame indices).
4) For each row in the CSV, reads the corresponding frame from the video.
5) Applies the model to the frame to get health metrics.
6) Writes a new CSV with the health columns appended.
"""

import csv
import cv2
import sys
from pathlib import Path

# Local import
try:
    from src.models.inference import load_model_and_scaler, predict_frame
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from src.models.inference import load_model_and_scaler, predict_frame

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Default paths (can be overridden)
# Maintaining original hardcoded paths for backward compatibility with user's specific workflow
# ideally these should be passed as arguments
DEFAULT_VIDEO_FOLDER = PROJECT_ROOT / "datasets" / "flights" / "DJI_20251114105612_0065_D"
DEFAULT_METADATA_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "extracted_metadata"
    / "DJI_20251114091511_0054_D"
    / "DJI_20251114091511_0054_D_metadata.csv"
)

def find_video_in_folder(folder: Path):
    """Finds a video file (mp4/mov/avi) inside the folder."""
    if not folder.exists():
        raise FileNotFoundError(f"Video folder not found: {folder}")

    candidates = []
    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() in [".mp4", ".mov", ".avi", ".mkv"]:
            candidates.append(file)

    if not candidates:
        raise FileNotFoundError(f"No video found in {folder}")

    # Return the first one found
    video_path = candidates[0]
    print(f"[INFO] Selected video: {video_path.name}")
    return video_path

def load_metadata_rows(csv_path: Path):
    """Reads metadata CSV and returns fieldnames and rows."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Metadata CSV not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    print(f"[INFO] Loaded {len(rows)} metadata rows")
    return fieldnames, rows

def write_metadata_with_health(original_fieldnames, rows, output_path: Path):
    """Writes the new CSV with health columns."""
    new_fields = [
        "health_ratio_percent",
        "unhealthy_ratio_percent",
        "health_status",
    ]
    # Add new fields if not present
    fieldnames = original_fieldnames + [f for f in new_fields if f not in original_fieldnames]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[INFO] Saved new CSV to: {output_path}")

def process_video_and_csv(video_folder, metadata_csv):
    """
    Main processing function.
    """
    video_path = find_video_in_folder(video_folder)
    fieldnames, rows = load_metadata_rows(metadata_csv)

    # Load Model
    print("[INFO] Loading model...")
    clf, scaler = load_model_and_scaler()
    print("[INFO] Model loaded successfully.")

    # Open Video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    print("[INFO] Processing frames...")
    total_rows = len(rows)
    processed_count = 0

    # We assume the CSV rows correspond to frames sequentially or have frame_index info.
    # The original script just iterated sequentially. We'll stick to that for now 
    # unless frame_index suggests we should seek.
    # Optimization: If frame_index is present, we could check if we need to skip frames.
    # For now, simplistic iteration as per original logic.

    for i, row in enumerate(rows):
        ret, frame = cap.read()
        if not ret:
            print(f"[WARN] Video ended early at row {i}. Stopping.")
            break

        # Compute health
        # using a small resize for speed, e.g. 256x256
        h_ratio, u_ratio, status = predict_frame(frame, clf, scaler, resize_dim=(256, 256))

        row["health_ratio_percent"] = f"{h_ratio:.2f}"
        row["unhealthy_ratio_percent"] = f"{u_ratio:.2f}"
        row["health_status"] = status

        processed_count += 1
        if (i + 1) % 50 == 0:
            print(f"  -> Processed {i+1}/{total_rows}")

    cap.release()

    # Save output
    output_csv = metadata_csv.with_name(metadata_csv.stem + "_with_health.csv")
    write_metadata_with_health(fieldnames, rows[:processed_count], output_csv)

def main():
    # Allow arguments or fallback to defaults
    video_folder = DEFAULT_VIDEO_FOLDER
    metadata_csv = DEFAULT_METADATA_CSV
    
    if len(sys.argv) > 1:
        # Simplistic arg parsing for now
        # Usage: python sync_video_csv.py [video_folder] [metadata_csv]
        video_folder = Path(sys.argv[1])
        if len(sys.argv) > 2:
            metadata_csv = Path(sys.argv[2])

    print(f"🚀 Starting sync_video_csv.py")
    print(f"📂 Video Folder: {video_folder}")
    print(f"📄 Metadata CSV: {metadata_csv}")
    
    try:
        process_video_and_csv(video_folder, metadata_csv)
        print("\n✅ Processing complete.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
