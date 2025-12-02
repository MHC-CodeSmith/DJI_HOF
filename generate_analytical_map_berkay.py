#!/usr/bin/env python3
"""
#file name :python3 generate_analytical_map.py
Generates an interactive analytical map with:

- Vegetation health heatmap (global + per track)
- Point layers per track (colored by health)
- Polyline ("long way") per track (flight path)
- Real satellite base map (Esri World Imagery)
"""

import csv
from pathlib import Path
from statistics import mean
from collections import defaultdict

# ---------------------------
# Helpers
# ---------------------------

def safe_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=None):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (ValueError, TypeError):
        return default

def load_metadata_with_health(csv_path: Path):
    """Reads the CSV with health index and returns a list of points."""
    points = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = safe_float(row.get("latitude"), None)
            lon = safe_float(row.get("longitude"), None)
            health = safe_float(row.get("health_index"), None)

            if lat is None or lon is None or health is None:
                continue

            # Grouping key (track / flight)
            video_name = row.get("video_name") or row.get("flight_id") or "unknown"

            # Try to order points inside each track
            frame_index_raw = row.get("frame_index") or row.get("FrameCnt") or ""
            frame_index = safe_int(frame_index_raw, default=None)

            points.append({
                "lat": lat,
                "lon": lon,
                "health": health,
                "video_name": video_name,
                "frame_index": frame_index,
                "frame_index_raw": frame_index_raw,
                "timestamp": row.get("timestamp", "")
            })
    return points

def calculate_bounds(points):
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    return {
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lon": min(lons),
        "max_lon": max(lons),
        "center_lat": mean(lats),
        "center_lon": mean(lons),
    }

def health_to_color(health, min_health, max_health):
    """
    Red → Yellow → Green gradient based on normalized health.
    0   → 0.5 →  1
    """
    if max_health == min_health:
        ratio = 0.5
    else:
        ratio = (health - min_health) / (max_health - min_health)
    ratio = max(0.0, min(1.0, ratio))

    if ratio <= 0.5:
        # Red -> Yellow
        r = 255
        g = int(2 * ratio * 255)
        b = 0
    else:
        # Yellow -> Green
        g = 255
        r = int((1 - (ratio - 0.5) * 2) * 255)
        b = 0
    return f"#{r:02x}{g:02x}{b:02x}"

# ---------------------------
# HTML builder
# ---------------------------

def build_map_html(points, bounds, output_path: Path):
    center_lat = bounds["center_lat"]
    center_lon = bounds["center_lon"]

    # Group points by track
    track_groups = defaultdict(list)
    for p in points:
        track_groups[p["video_name"]].append(p)

    # Sort each track by frame index if possible
    for pts in track_groups.values():
        pts.sort(key=lambda p: p["frame_index"] if p["frame_index"] is not None else 0)

    # Global min/max health
    health_values = [p["health"] for p in points]
    min_health = min(health_values)
    max_health = max(health_values)

    # ================
    # Global heatmap
    # ================
    global_heat_js = ",\n        ".join(
        f"[{p['lat']:.6f}, {p['lon']:.6f}, {(p['health'] / 100.0):.4f}]"
        for p in points
    )

    # Per-track JS
    track_layers_js = []
    overlays_entries = [
        # global heatmap added later
    ]

    for track_id, pts in track_groups.items():
        safe_id = track_id.replace("-", "_").replace(" ", "_").replace(".", "_")

        # Per-track heat data
        heat_js = ",\n        ".join(
            f"[{p['lat']:.6f}, {p['lon']:.6f}, {(p['health'] / 100.0):.4f}]"
            for p in pts
        )

        # Per-track points
        points_js = ",\n        ".join(
            f"""L.circleMarker([{p['lat']:.6f}, {p['lon']:.6f}], {{
                radius: 3,
                color: '{health_to_color(p['health'], min_health, max_health)}',
                fillColor: '{health_to_color(p['health'], min_health, max_health)}',
                fillOpacity: 0.9,
                weight: 0.5
            }}).bindPopup('Track: {track_id}<br>Health: {p['health']:.2f}%<br>Frame: {p['frame_index_raw']}<br>Timestamp: {p['timestamp']}')"""
            for p in pts
        )

        # Per-track polyline (long way of the flight)
        poly_coords_js = ",\n        ".join(
            f"[{p['lat']:.6f}, {p['lon']:.6f}]" for p in pts
        )

        track_layers_js.append(f"""
        // --- Track: {track_id} ---
        var heat_{safe_id} = L.heatLayer(
          [{heat_js}],
          {{
            radius: 25,
            blur: 30,
            maxZoom: 19,
            minOpacity: 0.35
          }}
        );

        var pontos_{safe_id} = L.layerGroup([{points_js}]);

        var path_{safe_id} = L.polyline(
          [{poly_coords_js}],
          {{
            color: '#3388ff',
            weight: 3,
            opacity: 0.8
          }}
        );
        """)

        overlays_entries.append(f"'Heatmap {track_id}': heat_{safe_id}")
        overlays_entries.append(f"'Points {track_id}': pontos_{safe_id}")
        overlays_entries.append(f"'Path {track_id} (Polyline)': path_{safe_id}")

    overlays_js = ",\n        ".join(overlays_entries)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Analytical Map per Track</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html, body, #map {{
    height: 100%;
    margin: 0;
    padding: 0;
  }}
  .legend {{
    position: absolute;
    bottom: 20px;
    left: 20px;
    background: white;
    padding: 10px;
    border-radius: 6px;
    box-shadow: 0 0 8px rgba(0,0,0,0.3);
    z-index: 1000;
    font-family: sans-serif;
    font-size: 12px;
  }}
  .legend-gradient {{
    width: 160px;
    height: 12px;
    background: linear-gradient(to right, #ff3333, #ffff66, #00cc44);
    border-radius: 3px;
    margin-top: 6px;
  }}
</style>
</head>
<body>
<div id="map"></div>

<div class="legend">
  <strong>Vegetation Health (%)</strong>
  <div class="legend-gradient"></div>
  <div style="display:flex;justify-content:space-between;">
    <span>Poor</span>
    <span>Medium</span>
    <span>Healthy</span>
  </div>
  <div style="margin-top:6px;">
    <span style="display:inline-block;width:10px;height:10px;background:#3388ff;margin-right:4px;border-radius:2px;"></span>
    <span style="vertical-align:middle;">Flight Path (Polyline)</span>
  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>

<script>
  // Base map with OSM + real satellite imagery
  var map = L.map('map').setView([{center_lat:.6f}, {center_lon:.6f}], 15);

  var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 22,
    attribution: '&copy; OpenStreetMap contributors'
  }}).addTo(map);

  var satellite = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
    {{
      maxZoom: 22,
      attribution: '&copy; Esri, Maxar, GeoEye, Earthstar Geographics'
    }}
  );

  // Global heatmap (all tracks)
  var heat_all = L.heatLayer(
    [{global_heat_js}],
    {{
      radius: 28,
      blur: 32,
      maxZoom: 19,
      minOpacity: 0.35
    }}
  );

  {''.join(track_layers_js)}

  var baseLayers = {{
    "OSM Map": osm,
    "Satellite (World Imagery)": satellite
  }};

  var overlays = {{
    "Global Heatmap (All Tracks)": heat_all,
    {overlays_js}
  }};

  L.control.layers(baseLayers, overlays, {{collapsed:false}}).addTo(map);

  // Fit bounds to all data
  var bounds = L.latLngBounds(
    [{bounds['min_lat']:.6f}, {bounds['min_lon']:.6f}],
    [{bounds['max_lat']:.6f}, {bounds['max_lon']:.6f}]
  );
  map.fitBounds(bounds.pad(0.05));
</script>
</body>
</html>
"""
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Analytical map created: {output_path}")

# ---------------------------
# Main
# ---------------------------

def main():
    base_dir = Path(__file__).parent
    csv_path = base_dir / "extracted_metadata" / "all_metadata_with_health.csv"
    if not csv_path.exists():
        print(f"❌ CSV not found: {csv_path}")
        return
    points = load_metadata_with_health(csv_path)
    if not points:
        print("❌ No points loaded (check CSV columns: latitude, longitude, health_index, video_name/frame_index)")
        return
    bounds = calculate_bounds(points)
    output_file = base_dir / "maps" / "map_per_track.html"
    build_map_html(points, bounds, output_file)

if __name__ == "__main__":
    main()
