# Drone Health Mapping Pipeline 🚁🌱

## Overview

This project implements a complete data processing pipeline for generating **Vegetation Health Maps** from drone video footage. It processes raw video and SRT metadata to calculate health indices (like VARI, ExG, TGI) using a **Pixelwise Machine Learning Model** (`SGDClassifier`).

The pipeline transforms raw drone data into interactive HTML maps that visualize:
1.  **Flight Trajectories** (Flight Map)
2.  **Vegetation Health Heatmaps** (Analytical Map)

## 📂 Project Structure

The workspace is organized modularly:

```text
/home/mhc/Germany/Drone/DJI_HOF/
│
├── main.py                     # 🚀 MAIN ENTRY POINT (Run everything from here)
│
├── datasets/                   # 📦 RAW DATA SOURCES
│   ├── PlantVillage/           # Labeled images for training
│   ├── Dataset_Hipolito_drone/ # Drone videos for training (weak supervision)
│   └── flights/                # Input Drone Flight Folders (e.g., DJI_..._D)
│
├── src/                        # 🛠️ SOURCE CODE
│   ├── ingestion/              # Metadata extraction from .SRT files
│   ├── models/                 # Model training & inference logic
│   ├── processing/             # Syncs Video Frames with Metadata & predicts Health
│   └── visualization/          # Generates HTML maps (Folium/Leaflet)
│
├── data/                       # 💾 GENERATED DATA
│   ├── models/                 # Saved models (pixelwise_sgd_classifier.pkl)
│   └── processed/              # Extracted CSVs and Health Data
│
└── backup/                     # 🧹 Legacy/Old scripts (safe to ignore)
```

## ⚙️ Setup & Requirements

1.  **Environment**: Ensure you are using the project's virtual environment.
    ```bash
    source venv/bin/activate
    ```
2.  **Dependencies**:
    *   `opencv-python`
    *   `numpy`
    *   `pandas`
    *   `scikit-learn`
    *   `joblib`
    *   `folium`
    *   `branca`
    *   `matplotlib` (for colormaps)

## 🚀 Usage

You can run the entire pipeline or individual steps using `main.py`.

### 1. Run Full Pipeline
To process all flight data found in `datasets/flights/` and generate maps:
```bash
python main.py pipeline
```
*This sequence runs: Extract -> Sync -> Map Flight -> Map Analytical.*

### 2. Individual Steps

*   **Train Model** (if needed):
    ```bash
    python main.py train
    ```
    *Trains the SGDClassifier using PlantVillage and Drone data.*

*   **Extract Metadata**:
    ```bash
    python main.py extract
    ```
    *Parses .SRT files from `datasets/flights/` into CSVs in `data/processed/`.*

*   **Calculate Health (Sync)**:
    ```bash
    python main.py sync
    ```
    *Applies the trained model to video frames, adding health indices to the CSVs.*

*   **Generate Maps**:
    ```bash
    python main.py map-flight       # Generates flight path map
    python main.py map-analytical   # Generates health heatmap
    ```

## 🧠 Model Details

*   **Type**: `SGDClassifier` (Stochastic Gradient Descent).
*   **Features**: Pixel-level extraction of:
    *   **VARI** (Visible Atmospherically Resistant Index)
    *   **ExG** (Excess Green)
    *   **TGI** (Triangular Greenness Index)
*   **Training Data**: Mixed dataset of **PlantVillage** (labeled leaves) and **Dataset_Hipolito_drone** (drone frames with weak labeling).

## 🗺️ Outputs

After running the pipeline, find your maps in `maps/`:
*   **`maps/flight_map.html`**: Shows the drone's path and altitude.
*   **`maps/analytical_map.html`**: Interactive Health Map containing:
    *   **Global Heatmap**: Interpolated view of vegetation health (Green=Healthy, Red=Unhealthy).
    *   **Per-Track Layers**: Toggleable layers for individual flights, showing heatmap, specific points, and flight paths.
    *   **Satellite Base**: Esri World Imagery background.

---
