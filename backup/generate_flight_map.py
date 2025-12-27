#!/usr/bin/env python3
"""
Generates an interactive map (Leaflet) showing flight tracks.
Uses only standard libraries and reads all_metadata_consolidated.csv.
"""

import csv
import json
from pathlib import Path
from statistics import mean


def load_metadata(csv_path):
    """Reads the consolidated CSV and returns a list of dictionaries with converted types."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                latitude = float(row.get("latitude", "") or 0)
                longitude = float(row.get("longitude", "") or 0)
            except ValueError:
                continue

            try:
                rel_alt = float(row.get("relative_altitude", "") or 0)
            except ValueError:
                rel_alt = None

            rows.append(
                {
                    "video_name": row.get("video_name", "unknown"),
                    "frame_index": row.get("frame_index"),
                    "timestamp": row.get("timestamp"),
                    "latitude": latitude,
                    "longitude": longitude,
                    "relative_altitude": rel_alt,
                    "absolute_altitude": row.get("absolute_altitude"),
                    "iso": row.get("iso"),
                    "shutter": row.get("shutter"),
                    "aperture": row.get("aperture"),
                    "ev": row.get("ev"),
                    "color_mode": row.get("color_mode"),
                    "focal_length": row.get("focal_length"),
                    "color_temperature": row.get("color_temperature"),
                }
            )
    return rows


def group_by_video(rows):
    """Groups all rows by their corresponding video_name and sorts each flight by frame_index."""
    grouped = {}
    for row in rows:
        grouped.setdefault(row["video_name"], []).append(row)

    # Sort each flight by frame_index
    for rows in grouped.values():
        rows.sort(key=lambda r: int(r["frame_index"]) if r["frame_index"] else 0)

    return grouped


def altitude_to_color(value, min_alt, max_alt):
    """Returns a hex color based on relative altitude using a blue-to-red gradient."""
    if value is None or min_alt is None or max_alt is None:
        return "#888888"

    if max_alt == min_alt:
        ratio = 0.5
    else:
        ratio = (value - min_alt) / (max_alt - min_alt)

    ratio = max(0.0, min(1.0, ratio))

    # Gradient from blue (#2c7bb6) to red (#d73027)
    start = (44, 123, 182)
    end = (215, 48, 39)

    r = int(start[0] + (end[0] - start[0]) * ratio)
    g = int(start[1] + (end[1] - start[1]) * ratio)
    b = int(start[2] + (end[2] - start[2]) * ratio)

    return f"#{r:02x}{g:02x}{b:02x}"


def build_map_html(flights, bounds, output_path):
    """Generates the HTML map and writes it to output_path."""
    center_lat = mean([bounds[0][0], bounds[1][0]])
    center_lon = mean([bounds[0][1], bounds[1][1]])

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Flight Map</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    body, html {{ margin: 0; padding: 0; height: 100%; font-family: sans-serif; }}
    #map {{ height: 100%; }}
    .legend {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: rgba(255,255,255,0.9);
      padding: 10px;
      border-radius: 4px;
      box-shadow: 0 0 8px rgba(0,0,0,0.2);
      font-size: 12px;
      line-height: 1.4;
    }}
    .legend-gradient {{
      background: linear-gradient(to right, #2c7bb6, #d73027);
      height: 10px;
      margin: 6px 0;
      border-radius: 2px;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="legend">
    <strong>Relative Altitude (m)</strong>
    <div class="legend-gradient"></div>
    <div style="display:flex;justify-content:space-between;">
      <span>{flights['altitude_range']['min']:.2f}</span>
      <span>{flights['altitude_range']['max']:.2f}</span>
    </div>
  </div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map').setView([{center_lat}, {center_lon}], 16);
    const bounds = {json.dumps(bounds)};
    map.fitBounds(bounds);

    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 22,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const flights = {json.dumps(flights['data'])};

    const palette = ["#e41a1c","#377eb8","#4daf4a","#984ea3","#ff7f00",
                     "#ffff33","#a65628","#f781bf","#999999","#66c2a5",
                     "#fc8d62","#8da0cb","#e78ac3","#a6d854","#ffd92f"];

    const colorByFlight = L.layerGroup().addTo(map);
    const colorByAltitude = L.layerGroup();

    flights.forEach((flight, idx) => {{
      const color = palette[idx % palette.length];
      const coords = flight.points.map(p => [p.latitude, p.longitude]);

      L.polyline(coords, {{
        color: color,
        weight: 2,
        opacity: 0.8
      }}).addTo(colorByFlight);

      flight.points.forEach(point => {{
        const popupHtml = `
          <strong>${{flight.video_name}}</strong><br/>
          Frame: ${{point.frame_index}}<br/>
          Timestamp: ${{point.timestamp}}<br/>
          Lat/Lon: ${{point.latitude.toFixed(6)}}, ${{point.longitude.toFixed(6)}}<br/>
          Rel. Altitude: ${{point.relative_altitude ?? 'N/A'}} m<br/>
          ISO: ${{point.iso}} | Shutter: ${{point.shutter}} | f/${{point.aperture}}
        `;

        L.circleMarker([point.latitude, point.longitude], {{
          radius: 4,
          color: color,
          fillColor: color,
          fillOpacity: 0.8,
          weight: 1
        }}).bindPopup(popupHtml).addTo(colorByFlight);

        L.circleMarker([point.latitude, point.longitude], {{
          radius: 4,
          color: point.altitude_color,
          fillColor: point.altitude_color,
          fillOpacity: 0.85,
          weight: 1
        }}).bindPopup(popupHtml).addTo(colorByAltitude);
      }});
    }});

    const overlays = {{
      "Color by Flight": colorByFlight,
      "Color by Altitude": colorByAltitude
    }};
    L.control.layers(null, overlays, {{ collapsed: false }}).addTo(map);
  </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"✅ Map created at: {output_path}")


def main():
    base_dir = Path(__file__).parent
    csv_path = base_dir / "extracted_metadata" / "all_metadata_consolidated.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Consolidated CSV not found: {csv_path}")

    rows = load_metadata(csv_path)
    if not rows:
        raise RuntimeError("No data available to generate the map.")

    all_lats = [r["latitude"] for r in rows]
    all_lons = [r["longitude"] for r in rows]

    bounds = [
        [min(all_lats), min(all_lons)],
        [max(all_lats), max(all_lons)],
    ]

    altitudes = [r["relative_altitude"] for r in rows if r["relative_altitude"] is not None]
    min_alt = min(altitudes) if altitudes else 0.0
    max_alt = max(altitudes) if altitudes else 0.0

    grouped = group_by_video(rows)

    flight_payload = {
        "data": [],
        "altitude_range": {"min": min_alt, "max": max_alt},
    }

    for video_name, points in grouped.items():
        flight_points = []
        for point in points:
            color = altitude_to_color(point["relative_altitude"], min_alt, max_alt)
            flight_points.append(
                {
                    "latitude": point["latitude"],
                    "longitude": point["longitude"],
                    "relative_altitude": point["relative_altitude"],
                    "frame_index": point["frame_index"],
                    "timestamp": point["timestamp"],
                    "iso": point["iso"],
                    "shutter": point["shutter"],
                    "aperture": point["aperture"],
                    "altitude_color": color,
                }
            )

        flight_payload["data"].append(
            {"video_name": video_name, "points": flight_points}
        )

    output_dir = base_dir / "maps"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "flight_map.html"
    build_map_html(flight_payload, bounds, output_file)


if __name__ == "__main__":
    main()
