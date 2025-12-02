#!/usr/bin/env python3
"""
Generates an interactive analytical map with vegetation health heatmap
and pontos layers per track (grouped by video_name).
"""

"""

It need to be added real satellite map function
HeatMap must be improved (It's not showing correctly so much)


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

def load_metadata_with_health(csv_path):
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
            points.append({
                "lat": lat,
                "lon": lon,
                "health": health,
                "video_name": row.get("video_name", "unknown"),
                "frame_index": row.get("frame_index", ""),
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
    """Red → Yellow → Green gradient based on normalized health."""
    if max_health == min_health:
        ratio = 0.5
    else:
        ratio = (health - min_health) / (max_health - min_health)
    ratio = max(0.0, min(1.0, ratio))
    if ratio <= 0.5:
        r = 255
        g = int(2 * ratio * 255)
        b = 0
    else:
        g = 255
        r = int((1 - (ratio - 0.5) * 2) * 255)
        b = 0
    return f"#{r:02x}{g:02x}{b:02x}"

# ---------------------------
# HTML builder
# ---------------------------

def build_map_html(points, bounds, output_path):
    center_lat = bounds["center_lat"]
    center_lon = bounds["center_lon"]

    # Group points by track
    track_groups = defaultdict(list)
    for p in points:
        track_groups[p["video_name"]].append(p)

    # Global min/max health
    health_values = [p["health"] for p in points]
    min_health = min(health_values)
    max_health = max(health_values)

    # Build JS for each track
    track_layers_js = []
    overlays_entries = []
    for track_id, pts in track_groups.items():
        # Heatmap data
        heat_js = ",\n        ".join(
            f"[{p['lat']:.6f}, {p['lon']:.6f}, {p['health']/100:.4f}]" for p in pts
        )
        # Points layer
        points_js = ",\n        ".join(
            f"""L.circleMarker([{p['lat']:.6f}, {p['lon']:.6f}], {{
                radius: 3,
                color: '{health_to_color(p['health'], min_health, max_health)}',
                fillColor: '{health_to_color(p['health'], min_health, max_health)}',
                fillOpacity: 0.8,
                weight: 0.5
            }}).bindPopup('Track: {track_id}<br>Health: {p['health']:.2f}%<br>Frame: {p['frame_index']}<br>Timestamp: {p['timestamp']}')"""
            for p in pts
        )
        safe_id = track_id.replace("-", "_").replace(" ", "_")
        track_layers_js.append(f"""
        var heat_{safe_id} = L.heatLayer([{heat_js}], {{radius:15, blur:20, minOpacity:0.4}});
        var pontos_{safe_id} = L.layerGroup([{points_js}]);
        """)
        overlays_entries.append(f"'Heatmap {track_id}': heat_{safe_id}")
        overlays_entries.append(f"'Pontos {track_id}': pontos_{safe_id}")

    overlays_js = ",\n        ".join(overlays_entries)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Mapa Analítico por Track</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>html,body,#map{{height:100%;margin:0;}}</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat/dist/leaflet-heat.js"></script>
<script>
var map = L.map('map').setView([{center_lat:.6f}, {center_lon:.6f}], 14);
var osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom:19}}).addTo(map);

{''.join(track_layers_js)}

var baseLayers = {{"OpenStreetMap": osm}};
var overlays = {{
    {overlays_js}
}};
L.control.layers(baseLayers, overlays, {{collapsed:false}}).addTo(map);

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
    print(f"✅ Map created: {output_path}")

# ---------------------------
# Main
# ---------------------------

def main():
    base_dir = Path(__file__).parent
    csv_path = base_dir / "extracted_metadata" / "all_metadata_with_health.csv"
    if not csv_path.exists():
        print("❌ CSV not found")
        return
    points = load_metadata_with_health(csv_path)
    if not points:
        print("❌ No points loaded")
        return
    bounds = calculate_bounds(points)
    output_file = base_dir / "maps" / "map_per_track.html"
    build_map_html(points, bounds, output_file)

if __name__ == "__main__":
    main()
