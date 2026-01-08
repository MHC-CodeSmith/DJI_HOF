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
import av
from pathlib import Path
from datetime import datetime

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
        "health_index",
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

        row["health_index"] = f"{h_ratio:.2f}"
        row["unhealthy_ratio_percent"] = f"{u_ratio:.2f}"
        row["health_status"] = status

        processed_count += 1
        if (i + 1) % 50 == 0:
            print(f"  -> Processed {i+1}/{total_rows}")

    cap.release()

    # Save output
    output_csv = metadata_csv.with_name(metadata_csv.stem + "_with_health.csv")
    write_metadata_with_health(fieldnames, rows[:processed_count], output_csv)

def process_video_stream(stream_url: str, output_csv_path: Path = None, metadata_csv_path: Path = None):
    """
    Processes a live video stream (RTMP/HTTP) and logs health analysis results to CSV in real-time.
    
    Args:
        stream_url: URL of the video stream (e.g., "rtmp://127.0.0.1/live")
        output_csv_path: Optional path for output CSV. If None, creates a timestamped file.
        metadata_csv_path: Optional path to metadata CSV for additional context (GPS, etc.)
    """
    # Determine output CSV path
    if output_csv_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = PROJECT_ROOT / "data" / "processed" / "stream_logs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_csv_path = output_dir / f"stream_health_{timestamp}.csv"
    else:
        output_csv_path = Path(output_csv_path)
        output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[INFO] Output CSV: {output_csv_path}")
    
    # Load metadata if provided (optional)
    metadata_map = {}
    if metadata_csv_path and Path(metadata_csv_path).exists():
        print(f"[INFO] Loading metadata from: {metadata_csv_path}")
        _, metadata_rows = load_metadata_rows(Path(metadata_csv_path))
        # Build frame index map if frame_index exists
        for row in metadata_rows:
            if row.get("frame_index"):
                try:
                    frame_idx = int(row["frame_index"])
                    metadata_map[frame_idx] = row
                except ValueError:
                    pass
        print(f"[INFO] Loaded metadata for {len(metadata_map)} frames")
    
    # Load Model
    print("[INFO] Loading model...")
    clf, scaler = load_model_and_scaler()
    print("[INFO] Model loaded successfully.")

    # Define CSV fieldnames
    base_fields = [
        "frame_number",
        "timestamp",
        "health_index",
        "unhealthy_ratio_percent",
        "health_status",
    ]
    
    # Add optional metadata fields if metadata is available
    metadata_fields = [
        "latitude", "longitude", "relative_altitude", "absolute_altitude",
        "iso", "shutter", "aperture", "ev", "color_mode", "focal_length", "color_temperature"
    ]
    
    # Use metadata fields if we have metadata, otherwise just base fields
    if metadata_map:
        fieldnames = base_fields + metadata_fields
    else:
        fieldnames = base_fields
    
    # Open CSV file for incremental writing
    csv_file = open(output_csv_path, "w", newline="", encoding="utf-8")
    csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    csv_writer.writeheader()
    csv_file.flush()  # Write header immediately
    
    print("[INFO] Opening video stream...")
    container = av.open(stream_url)
    try:
        container.streams.video[0]
    except Exception as e:
        container.close()
        csv_file.close()
        raise RuntimeError(f"Could not open video stream: {stream_url}. Error: {e}")

    print("[INFO] Processing stream (press ESC to stop)...")
    frame_count = 0
    processed_count = 0
    
    try:
        for frame in container.decode(video=0):
            img = frame.to_ndarray(format="bgr24")
            
            # Compute health metrics
            h_ratio, u_ratio, status = predict_frame(img, clf, scaler, resize_dim=(256, 256))
            
            # Build row data
            row = {
                "frame_number": str(frame_count),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],  # Format: YYYY-MM-DD HH:MM:SS.mmm
                "health_index": f"{h_ratio:.2f}",
                "unhealthy_ratio_percent": f"{u_ratio:.2f}",
                "health_status": status,
            }
            
            # Add metadata if available
            if metadata_map and frame_count in metadata_map:
                metadata = metadata_map[frame_count]
                for field in metadata_fields:
                    row[field] = metadata.get(field, "")
            elif metadata_map:
                # Fill with empty values if metadata not found for this frame
                for field in metadata_fields:
                    row[field] = ""
            
            # Write to CSV immediately
            csv_writer.writerow(row)
            csv_file.flush()  # Ensure data is written immediately
            
            processed_count += 1
            
            # Progress update every 30 frames
            if processed_count % 30 == 0:
                print(f"  -> Processed {processed_count} frames | Health: {h_ratio:.1f}% | Status: {status}")
            
            frame_count += 1
            
    except KeyboardInterrupt:
        print("\n[INFO] Stream processing interrupted by user.")
    except Exception as e:
        print(f"\n[ERROR] Error processing stream: {e}")
        raise
    finally:
        csv_file.close()
        container.close()
        print(f"[INFO] Stream processing complete. Processed {processed_count} frames.")
        print(f"[INFO] Results saved to: {output_csv_path}")



def process_batch(flights_dir: Path, processed_dir: Path):
    """
    Iterates over all flight folders in flights_dir and processes them.
    """
    if not flights_dir.exists():
        print(f"❌ Flights directory not found: {flights_dir}")
        return

    flight_folders = [f for f in flights_dir.iterdir() if f.is_dir()]
    print(f"📂 Found {len(flight_folders)} flight folders in {flights_dir}")

    total_processed = 0

    for folder in sorted(flight_folders):
        video_name = folder.name
        print(f"\n🔄 Processing Flight: {video_name}")
        
        # Determine paths
        # Video is in datasets/flights/<VideoName>/*.mp4
        # Metadata is in data/processed/extracted_metadata/<VideoName>/<VideoName>_metadata.csv
        
        metadata_csv_folder = processed_dir / video_name
        metadata_csv = metadata_csv_folder / f"{video_name}_metadata.csv"
        
        if not metadata_csv.exists():
            print(f"   ⚠️ Metadata CSV not found: {metadata_csv} (Skipping)")
            continue
            
        try:
            process_video_and_csv(folder, metadata_csv)
            total_processed += 1
        except Exception as e:
            print(f"   ❌ Error processing {video_name}: {e}")

    print(f"\n✅ Batch processing complete. Processed {total_processed}/{len(flight_folders)} flights.")

def main():
    # Allow arguments or fallback to defaults
    
    # Check if we are in batch mode (no args provided, or batch flag)
    # Default behavior: run batch on project structure
    
    base_dir = PROJECT_ROOT
    flights_dir = base_dir / "datasets" / "flights"
    processed_dir = base_dir / "data" / "processed" / "extracted_metadata"

    # Check for stream mode (URL starts with rtmp://, http://, https://, or stream://)
    if len(sys.argv) > 1:
        first_arg = sys.argv[1].lower()
        if first_arg.startswith(("rtmp://", "http://", "https://", "stream://", "udp://")):
            # Stream mode
            stream_url = sys.argv[1]
            output_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else None
            metadata_csv = Path(sys.argv[3]) if len(sys.argv) > 3 else None
            
            print(f"🚀 Running Live Stream Processing")
            print(f"📡 Stream URL: {stream_url}")
            if output_csv:
                print(f"📄 Output CSV: {output_csv}")
            if metadata_csv:
                print(f"📋 Metadata CSV: {metadata_csv}")
            
            try:
                process_video_stream(stream_url, output_csv, metadata_csv)
                print("\n✅ Stream processing complete.")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                sys.exit(1)
            return
    
    # Support single file mode validation if args provided
    if len(sys.argv) > 1 and sys.argv[1] != "batch":
        video_folder = Path(sys.argv[1])
        metadata_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_METADATA_CSV
        print(f"🚀 Running Single Video Sync")
        try:
            process_video_and_csv(video_folder, metadata_csv)
            print("\n✅ Processing complete.")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
        return

    # Batch Mode
    print(f"🚀 Starting Batch Sync (All Videos)")
    print(f"📂 Flights Dir: {flights_dir}")
    print(f"📄 Metadata Dir: {processed_dir}")
    
    process_batch(flights_dir, processed_dir)

if __name__ == "__main__":
    main()
