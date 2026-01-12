
# 🚁 Final Drone Mapping Workflow

This guide captures the **Simplified, Verified Process** to go from Flight to Map.

## 🟢 Phase 1: Live Flight (Monitoring)
**Goal:** See the Green/Red health overlay in real-time to guide your flight.

1.  **Start the Drone Livestream** (RTMP).
2.  **Run the Viewer:**
    ```bash
    .venv/bin/python src/processing/sync_video_csv.py rtmp://127.0.0.1:1998/live/drone
    ```
    *   *Result:* You see the analysis on screen.
    *   *Note:* The CSV logs generated here are for **backup only** (timestamp sync is loose).

---

## 💾 Phase 2: Data Transfer (Post-Flight)
**Goal:** Get the **High-Precision Data** (GPS + 4K Video) for the map.

1.  Land the Drone.
2.  **Copy 2 files** from the SD Card (use USB or QuickTransfer to Phone -> PC):
    *   `DJI_xxxx.MP4` (The Video)
    *   `DJI_xxxx.SRT` (The GPS Logs)
3.  **Save them** to a new folder, e.g.:
    *   `datasets/flights/Flight_01/`

---

## ⚙️ Phase 3: Processing (The Merge)
**Goal:** Combine the High-Quality Video with the Exact GPS to make the Map CSV.

### Step A: Extract GPS
Run this to pull the GPS data from the subtitle file:
```bash
# Replace path with your actual SRT file
python src/ingestion/extract_metadata.py datasets/flights/Flight_01/DJI_xxxx.SRT
```
*   **Output:** Creates `data/processed/extracted_metadata/Flight_01/Flight_01_metadata.csv`

### Step B: Sync Health Analysis
Run this to process the video and attach Health Data to the GPS:
```bash
# Replace paths with your actual Video and the CSV from Step A
.venv/bin/python src/processing/sync_video_csv.py \
    datasets/flights/Flight_01/DJI_xxxx.MP4 \
    data/processed/extracted_metadata/Flight_01/Flight_01_metadata.csv
```

---

## ✅ Final Result
You now have a single CSV file containing:
*   **Exact GPS** (Latitude/Longitude)
*   **Health Index** (0.0 - 1.0)
*   **Frame Number** (Perfectly synced)

File location: `data/processed/extracted_metadata/Flight_01/..._with_health.csv`
**Use this file for your Mapping Software.**
