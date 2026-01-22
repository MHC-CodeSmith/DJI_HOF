#!/usr/bin/env python3
"""
Web server for real-time flight visualization.
Serves the map interface and provides API endpoints for CSV data.
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pathlib import Path
import csv
import json
from datetime import datetime
from typing import List, Dict

HOST = '127.0.0.1'
PORT = 5001

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
app = Flask(__name__, static_folder=str(PROJECT_ROOT / "src" / "web"), static_url_path='')
CORS(app)  # Enable CORS for API access

# Paths
STREAM_LOGS_DIR = PROJECT_ROOT / "data" / "processed" / "extracted_metadata"

def safe_float(value, default=None):
    """Safely convert to float."""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def load_latest_stream_csv() -> Path:
    """Find the most recent stream CSV file."""
    if not STREAM_LOGS_DIR.exists():
        return None
    
    # TODO: change the filename
    csv_files = list(STREAM_LOGS_DIR.glob("for*.csv"))
    if not csv_files:
        return None
    
    # Sort by modification time, newest first
    csv_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return csv_files[0]

def read_csv_data(csv_path: Path) -> List[Dict]:
    """Read CSV and return list of points with GPS and health data."""
    if not csv_path or not csv_path.exists():
        return []
    
    points = []
    #print(f"Reading CSV: {csv_path}")
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = safe_float(row.get("latitude"))
            lon = safe_float(row.get("longitude"))
            health = safe_float(row.get("health_index"))
            
            # Skip if missing essential data
            if lat is None or lon is None or health is None:
                continue
            
            points.append({
                "lat": lat,
                "lon": lon,
                "health_index": health,
                "unhealthy_ratio": safe_float(row.get("unhealthy_ratio_percent"), 0),
                "health_status": row.get("health_status", "Unknown"),
                "frame_number": row.get("frame_number", ""),
                "timestamp": row.get("timestamp", ""),
                "altitude": safe_float(row.get("relative_altitude")),
            })
    
    return points

@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory(PROJECT_ROOT / "src" / "web", 'index.html')

@app.route('/app.js')
def app_js():
    """Serve the JavaScript file."""
    return send_from_directory(PROJECT_ROOT / "src" / "web", 'app.js')

@app.route('/api/points')
def get_points():
    """
    API endpoint: Get GPS points with smart limiting for initial load.
    Returns last 5,000 points with sampling (every 10th point = 500 points).
    """
    csv_path = load_latest_stream_csv()
    if not csv_path:
        return jsonify({
            "success": False,
            "message": "No stream data available yet",
            "points": []
        })
    
    # Get parameters with defaults
    limit = request.args.get('limit', default=5000, type=int)
    
    sample_rate = request.args.get('sample', default=10, type=int)
    sample_rate = max(1, min(sample_rate, 100))  # Between 1 and 100
    
    # Read all points
    all_points = read_csv_data(csv_path)
    
    if not all_points:
        return jsonify({
            "success": True,
            "csv_file": csv_path.name,
            "last_updated": datetime.fromtimestamp(csv_path.stat().st_mtime).isoformat(),
            "total_points": 0,
            "sample_rate": sample_rate,
            "returned_count": 0,
            "points": []
        })
    
    # Take last N points (most recent)
    recent_points = all_points[-limit:] if len(all_points) > limit else all_points
    
    # Sample points (every Nth point)
    sampled_points = recent_points[::sample_rate]

    return jsonify({
        "success": True,
        "csv_file": csv_path.name,
        "last_updated": datetime.fromtimestamp(csv_path.stat().st_mtime).isoformat(),
        "total_points": len(all_points),
        "sample_rate": sample_rate,
        "returned_count": len(sampled_points),
        "points": sampled_points
    })

@app.route('/api/stats')
def get_stats():
    """API endpoint: Get aggregated statistics."""
    csv_path = load_latest_stream_csv()
    if not csv_path:
        return jsonify({
            "success": False,
            "message": "No stream data available"
        })
    
    points = read_csv_data(csv_path)
    
    if not points:
        return jsonify({
            "success": False,
            "message": "No valid points found"
        })
    
    # Calculate statistics
    total_points = len(points)
    healthy_count = sum(1 for p in points if p["health_status"] == "Healthy")
    moderate_count = sum(1 for p in points if p["health_status"] == "Moderate")
    unhealthy_count = sum(1 for p in points if p["health_status"] == "Unhealthy")
    
    avg_health = sum(p["health_index"] for p in points) / total_points if total_points > 0 else 0
    
    # Calculate bounds
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    
    return jsonify({
        "success": True,
        "total_points": total_points,
        "average_health": round(avg_health, 2),
        "healthy_count": healthy_count,
        "moderate_count": moderate_count,
        "unhealthy_count": unhealthy_count,
        "bounds": {
            "min_lat": min(lats) if lats else 0,
            "max_lat": max(lats) if lats else 0,
            "min_lon": min(lons) if lons else 0,
            "max_lon": max(lons) if lons else 0,
            "center_lat": sum(lats) / len(lats) if lats else 0,
            "center_lon": sum(lons) / len(lons) if lons else 0,
        },
        "last_updated": datetime.fromtimestamp(csv_path.stat().st_mtime).isoformat()
    })

@app.route('/api/points/new')
def get_new_points():
    """
    API endpoint: Get only new points since last frame number (for incremental updates).
    Query parameter: ?since=<frame_number>
    """
    csv_path = load_latest_stream_csv()
    if not csv_path:
        return jsonify({
            "success": False,
            "message": "No stream data available yet",
            "points": []
        })
    
    # Get last known frame number from client
    last_frame = request.args.get('since', default=0, type=int)
    
    points = read_csv_data(csv_path)
    
    if not points:
        return jsonify({
            "success": True,
            "points": [],
            "total_points": 0,
            "new_count": 0
        })
    
    # Filter points with frame_number > last_frame
    new_points = [
        p for p in points 
        if p.get("frame_number") and safe_float(p["frame_number"], 0) > last_frame
    ]
    
    return jsonify({
        "success": True,
        "points": new_points,
        "total_points": len(points),
        "new_count": len(new_points)
    })

@app.route('/api/latest')
def get_latest():
    """API endpoint: Get only the latest point (for real-time updates)."""
    csv_path = load_latest_stream_csv()
    if not csv_path:
        return jsonify({"success": False, "point": None})
    
    points = read_csv_data(csv_path)
    if not points:
        return jsonify({"success": False, "point": None})
    
    # Return the last point (most recent)
    return jsonify({
        "success": True,
        "point": points[-1],
        "total_points": len(points)
    })



if __name__ == '__main__':
    print("🚀 Starting web server...")
    print("📡 API endpoints:")
    print(f"   - http://localhost:{PORT}/ (Map interface)")
    print(f"   - http://localhost:{PORT}/api/points (Initial load: sampled points)")
    print(f"   - http://localhost:{PORT}/api/points/new?since=<frame> (Incremental updates)")
    print(f"   - http://localhost:{PORT}/api/stats (Statistics)")
    print(f"   - http://localhost:{PORT}/api/latest (Latest point)")
    print("\n💡 Make sure sync_video_csv.py is running to generate CSV data!")
    
    app.run(host=HOST, port=PORT, debug=True)