#!/usr/bin/env python3
"""
Generates an interactive analytical map with a vegetation health heatmap.
Focused on scientific data analysis and visualization.
Includes spatial interpolation and multiple visualization layers.
"""

import csv
import json
import math
from pathlib import Path
from statistics import mean
from collections import defaultdict


def load_metadata_with_health(csv_path):
    """Reads the CSV with health index and returns a list of points."""
    points = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row.get("latitude", "") or 0)
                lon = float(row.get("longitude", "") or 0)
                health = float(row.get("health_index", "") or 0)
            except (ValueError, TypeError):
                continue
            
            if lat == 0 and lon == 0:
                continue
                
            points.append({
                "lat": lat,
                "lon": lon,
                "health": health,
                "frame_index": row.get("frame_index", ""),
                "timestamp": row.get("timestamp", ""),
                "video_name": row.get("video_name", ""),
                "relative_altitude": row.get("relative_altitude", ""),
            })
    
    return points


def calculate_bounds(points):
    """Computes the bounding box of the flight area."""
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


def create_interpolation_grid(points, grid_size=100):
    """
    Creates an interpolated grid using inverse distance weighting (IDW).
    grid_size: number of cells per dimension (total = grid_size^2)
    """
    bounds = calculate_bounds(points)
    
    lat_step = (bounds["max_lat"] - bounds["min_lat"]) / grid_size
    lon_step = (bounds["max_lon"] - bounds["min_lon"]) / grid_size
    
    grid_points = []
    
    # IDW interpolation parameters
    power = 2.0  # distance exponent (higher = more localized influence)
    max_distance = 0.001  # ~111 meters
    
    for i in range(grid_size + 1):
        for j in range(grid_size + 1):
            grid_lat = bounds["min_lat"] + i * lat_step
            grid_lon = bounds["min_lon"] + j * lon_step
            
            # IDW computation
            weighted_sum = 0.0
            weight_sum = 0.0
            
            for point in points:
                # Distance in degrees (approximation)
                lat_diff = grid_lat - point["lat"]
                lon_diff = grid_lon - point["lon"]
                distance = math.sqrt(lat_diff**2 + lon_diff**2)
                
                if distance < max_distance:
                    if distance < 0.00001:  # Very close → use direct value
                        weighted_sum = point["health"]
                        weight_sum = 1.0
                        break
                    
                    weight = 1.0 / (distance ** power)
                    weighted_sum += point["health"] * weight
                    weight_sum += weight
            
            if weight_sum > 0:
                interpolated_health = weighted_sum / weight_sum
                grid_points.append({
                    "lat": grid_lat,
                    "lon": grid_lon,
                    "health": round(interpolated_health, 2)
                })
    
    return grid_points


def health_to_color(health, min_health, max_health):
    """Converts vegetation health index (0–100) to an RGB color using a green–red gradient."""
    if max_health == min_health:
        ratio = 0.5
    else:
        ratio = (health - min_health) / (max_health - min_health)
    
    ratio = max(0.0, min(1.0, ratio))
    
    # Gradient: Green (healthy 100%) → Yellow → Orange → Red (poor 0%)
    if ratio > 0.66:  # Green to yellow
        r = int(255 * (1 - (ratio - 0.66) / 0.34))
        g = 255
        b = 0
    elif ratio > 0.33:  # Yellow to orange
        r = 255
        g = 255
        b = int(255 * (1 - (ratio - 0.33) / 0.33))
    else:  # Orange to red
        r = 255
        g = int(255 * (ratio / 0.33))
        b = 0
    
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    
    return f"#{r:02x}{g:02x}{b:02x}"


def calculate_statistics(points):
    """Computes descriptive statistics for vegetation health."""
    health_values = [p["health"] for p in points]
    
    if not health_values:
        return {}
    
    health_values.sort()
    n = len(health_values)
    
    return {
        "count": n,
        "min": min(health_values),
        "max": max(health_values),
        "mean": mean(health_values),
        "median": health_values[n // 2] if n > 0 else 0,
        "q25": health_values[n // 4] if n >= 4 else health_values[0],
        "q75": health_values[3 * n // 4] if n >= 4 else health_values[-1],
    }


def build_analytical_map_html(points, grid_points, bounds, stats, output_path):
    """Generates the HTML for the analytical map."""
    center_lat = bounds["center_lat"]
    center_lon = bounds["center_lon"]
    
    # Extract min/max health
    health_values = [p["health"] for p in points]
    min_health = min(health_values) if health_values else 0
    max_health = max(health_values) if health_values else 100
    
    # Prepare heatmap data
    heatmap_data = [[p["lat"], p["lon"], p["health"]] for p in points]
    
    # (HTML content remains in Portuguese as originally written)
    
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
...
</html>
"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ Mapa analítico criado: {output_path}")


def main():
    base_dir = Path(__file__).parent
    csv_path = base_dir / "extracted_metadata" / "all_metadata_with_health.csv"
    
    if not csv_path.exists():
        print(f"❌ Arquivo não encontrado: {csv_path}")
        print("   Execute primeiro: python3 add_health_index.py")
        return
    
    print("🚀 Gerando mapa analítico com índice de saúde\n")
    
    # Load data
    print("📖 Carregando dados...")
    points = load_metadata_with_health(csv_path)
    
    if not points:
        print("❌ Nenhum ponto encontrado!")
        return
    
    print(f"   ✅ {len(points):,} pontos carregados")
    
    # Compute bounds
    print("\n🗺️  Calculando área de voo...")
    bounds = calculate_bounds(points)
    print(f"   Latitude: {bounds['min_lat']:.6f} a {bounds['max_lat']:.6f}")
    print(f"   Longitude: {bounds['min_lon']:.6f} a {bounds['max_lon']:.6f}")
    
    # Statistics
    print("\n📊 Calculando estatísticas...")
    stats = calculate_statistics(points)
    print(f"   Saúde média: {stats['mean']:.2f}%")
    print(f"   Saúde mín/máx: {stats['min']:.2f}% / {stats['max']:.2f}%")
    
    # Create interpolation grid
    print("\n🔢 Criando grid interpolado (isso pode levar alguns segundos)...")
    grid_points = create_interpolation_grid(points, grid_size=80)
    print(f"   ✅ Grid criado com {len(grid_points):,} células")
    
    # Generate HTML map
    print("\n🎨 Gerando mapa HTML...")
    output_dir = base_dir / "maps"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "analytical_map.html"
    
    build_analytical_map_html(points, grid_points, bounds, stats, output_file)
    
    print(f"\n{'='*80}")
    print("✅ Processamento concluído!")
    print(f"   Mapa salvo em: {output_file}")
    print(f"   Abra o arquivo no navegador para visualizar")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
