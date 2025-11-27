#!/usr/bin/env python3
"""
Gera mapa analítico interativo com heatmap do índice de saúde da vegetação.
Focado em análise e visualização científica dos dados.
Inclui interpolação espacial e múltiplas camadas de visualização.
"""

import csv
import json
import math
from pathlib import Path
from statistics import mean
from collections import defaultdict


def load_metadata_with_health(csv_path):
    """Lê o CSV com índice de saúde e retorna lista de pontos."""
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
    """Calcula os bounds (limites) da área de voo."""
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
    Cria uma grade interpolada usando interpolação por distância inversa ponderada (IDW).
    grid_size: número de células por dimensão (total = grid_size^2)
    """
    bounds = calculate_bounds(points)
    
    lat_step = (bounds["max_lat"] - bounds["min_lat"]) / grid_size
    lon_step = (bounds["max_lon"] - bounds["min_lon"]) / grid_size
    
    grid_points = []
    
    # Parâmetros da interpolação IDW
    power = 2.0  # potência da distância (maior = mais localizado)
    max_distance = 0.001  # ~111 metros
    
    for i in range(grid_size + 1):
        for j in range(grid_size + 1):
            grid_lat = bounds["min_lat"] + i * lat_step
            grid_lon = bounds["min_lon"] + j * lon_step
            
            # IDW interpolation
            weighted_sum = 0.0
            weight_sum = 0.0
            
            for point in points:
                # Distância em graus (aproximação)
                lat_diff = grid_lat - point["lat"]
                lon_diff = grid_lon - point["lon"]
                distance = math.sqrt(lat_diff**2 + lon_diff**2)
                
                if distance < max_distance:
                    if distance < 0.00001:  # Muito próximo, usa o valor direto
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
    """Converte índice de saúde (0-100) para cor RGB usando gradiente verde-vermelho."""
    if max_health == min_health:
        ratio = 0.5
    else:
        ratio = (health - min_health) / (max_health - min_health)
    
    ratio = max(0.0, min(1.0, ratio))
    
    # Gradiente: Verde (saudável 100%) -> Amarelo -> Laranja -> Vermelho (não saudável 0%)
    if ratio > 0.66:  # Verde para amarelo
        r = int(255 * (1 - (ratio - 0.66) / 0.34))
        g = 255
        b = 0
    elif ratio > 0.33:  # Amarelo para laranja
        r = 255
        g = 255
        b = int(255 * (1 - (ratio - 0.33) / 0.33))
    else:  # Laranja para vermelho
        r = 255
        g = int(255 * (ratio / 0.33))
        b = 0
    
    # Garante valores válidos
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    
    return f"#{r:02x}{g:02x}{b:02x}"


def calculate_statistics(points):
    """Calcula estatísticas do índice de saúde."""
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
    """Gera o HTML do mapa analítico."""
    center_lat = bounds["center_lat"]
    center_lon = bounds["center_lon"]
    
    # Preparar dados para JavaScript
    health_values = [p["health"] for p in points]
    min_health = min(health_values) if health_values else 0
    max_health = max(health_values) if health_values else 100
    
    # Preparar pontos para heatmap
    heatmap_data = [[p["lat"], p["lon"], p["health"]] for p in points]
    
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Análise de Saúde da Vegetação - Mapa Interativo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  
  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  
  <!-- Leaflet Heat Plugin -->
  <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
  
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    
    body, html {{
      height: 100%;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      overflow: hidden;
    }}
    
    #map {{
      height: 100%;
      width: 100%;
    }}
    
    .control-panel {{
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(255, 255, 255, 0.95);
      padding: 15px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.3);
      max-width: 300px;
      z-index: 1000;
      font-size: 13px;
      max-height: 90vh;
      overflow-y: auto;
    }}
    
    .control-panel h3 {{
      margin: 0 0 10px 0;
      font-size: 16px;
      color: #333;
      border-bottom: 2px solid #4CAF50;
      padding-bottom: 5px;
    }}
    
    .stat-box {{
      background: #f5f5f5;
      padding: 8px;
      margin: 8px 0;
      border-radius: 4px;
      border-left: 3px solid #4CAF50;
    }}
    
    .stat-label {{
      font-weight: bold;
      color: #555;
      font-size: 11px;
      text-transform: uppercase;
    }}
    
    .stat-value {{
      font-size: 18px;
      color: #333;
      margin-top: 2px;
    }}
    
    .legend {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: rgba(255, 255, 255, 0.95);
      padding: 12px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.3);
      z-index: 1000;
    }}
    
    .legend h4 {{
      margin: 0 0 8px 0;
      font-size: 14px;
    }}
    
    .legend-gradient {{
      width: 200px;
      height: 20px;
      background: linear-gradient(to right, #ff0000, #ffff00, #00ff00);
      border-radius: 4px;
      margin: 5px 0;
    }}
    
    .legend-labels {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #666;
    }}
    
    .layer-control {{
      margin: 10px 0;
      padding: 8px;
      background: #f9f9f9;
      border-radius: 4px;
    }}
    
    .layer-control label {{
      display: block;
      margin: 5px 0;
      cursor: pointer;
    }}
    
    .layer-control input[type="range"] {{
      width: 100%;
      margin: 5px 0;
    }}
    
    .info-box {{
      background: #e3f2fd;
      padding: 8px;
      margin: 8px 0;
      border-radius: 4px;
      font-size: 11px;
      color: #1976d2;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  
  <div class="control-panel">
    <h3>📊 Painel de Análise</h3>
    
    <div class="stat-box">
      <div class="stat-label">Total de Pontos</div>
      <div class="stat-value">{stats['count']:,}</div>
    </div>
    
    <div class="stat-box">
      <div class="stat-label">Saúde Média</div>
      <div class="stat-value">{stats['mean']:.2f}%</div>
    </div>
    
    <div class="stat-box">
      <div class="stat-label">Saúde Mín/Máx</div>
      <div class="stat-value">{stats['min']:.1f}% / {stats['max']:.1f}%</div>
    </div>
    
    <div class="stat-box">
      <div class="stat-label">Mediana</div>
      <div class="stat-value">{stats['median']:.2f}%</div>
    </div>
    
    <div class="info-box">
      💡 Use os controles abaixo para alternar entre visualizações
    </div>
    
    <div class="layer-control">
      <label>
        <input type="checkbox" id="showHeatmap" checked> Heatmap
      </label>
      <label>
        <input type="range" id="heatmapRadius" min="10" max="50" value="25">
        Raio Heatmap: <span id="radiusValue">25</span>px
      </label>
    </div>
    
    <div class="layer-control">
      <label>
        <input type="checkbox" id="showGrid" checked> Grid Interpolado
      </label>
      <label>
        <input type="range" id="gridOpacity" min="0" max="100" value="60">
        Opacidade: <span id="opacityValue">60</span>%
      </label>
    </div>
    
    <div class="layer-control">
      <label>
        <input type="checkbox" id="showPoints"> Pontos Originais
      </label>
    </div>
  </div>
  
  <div class="legend">
    <h4>Índice de Saúde da Vegetação (%)</h4>
    <div class="legend-gradient"></div>
    <div class="legend-labels">
      <span>0% (Ruim)</span>
      <span>50%</span>
      <span>100% (Excelente)</span>
    </div>
  </div>
  
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    // Inicializar mapa
    const map = L.map('map').setView([{center_lat}, {center_lon}], 17);
    
    // Camadas de base
    const osmLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 22,
      attribution: '&copy; OpenStreetMap contributors'
    }});
    
    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 22,
      attribution: '&copy; Esri, Maxar, GeoEye, Earthstar Geographics'
    }});
    
    osmLayer.addTo(map);
    
    // Controle de camadas base
    const baseLayers = {{
      "Mapa": osmLayer,
      "Satélite": satelliteLayer
    }};
    
    // Dados
    const points = {json.dumps(points)};
    const gridPoints = {json.dumps(grid_points)};
    const bounds = {json.dumps([[bounds["min_lat"], bounds["min_lon"]], [bounds["max_lat"], bounds["max_lon"]]])};
    const minHealth = {min_health};
    const maxHealth = {max_health};
    
    // Ajustar bounds
    map.fitBounds(bounds, {{ padding: [20, 20] }});
    
    // Função de cor
    function healthToColor(health) {{
      const ratio = (health - minHealth) / (maxHealth - minHealth);
      const r = ratio > 0.66 ? Math.floor(255 * (1 - (ratio - 0.66) / 0.34)) :
               ratio > 0.33 ? 255 : 255;
      const g = ratio > 0.66 ? 255 :
               ratio > 0.33 ? 255 : Math.floor(255 * (ratio / 0.33));
      const b = ratio > 0.66 ? 0 :
               ratio > 0.33 ? Math.floor(255 * (1 - (ratio - 0.33) / 0.33)) : 0;
      return `rgb(${{Math.max(0,Math.min(255,r))}},${{Math.max(0,Math.min(255,g))}},${{Math.max(0,Math.min(255,b))}})`;
    }}
    
    // Preparar dados para heatmap (normalizados para intensidade 0-1)
    const heatmapData = points.map(p => [p.lat, p.lon, (p.health - minHealth) / (maxHealth - minHealth) * 100]);
    
    // Heatmap layer
    let heatmapLayer = L.heatLayer(heatmapData, {{
      radius: 25,
      blur: 15,
      maxZoom: 18,
      gradient: {{
        0.0: 'red',
        0.5: 'yellow',
        1.0: 'green'
      }},
      opacity: 0.6
    }});
    
    // Grid interpolado layer
    let gridLayer = L.layerGroup();
    gridPoints.forEach(point => {{
      const color = healthToColor(point.health);
      L.circle([point.lat, point.lon], {{
        radius: 3,
        fillColor: color,
        color: color,
        weight: 1,
        opacity: 0.6,
        fillOpacity: 0.6
      }}).bindPopup(`Saúde: ${{point.health.toFixed(1)}}%`).addTo(gridLayer);
    }});
    
    // Pontos originais
    let pointsLayer = L.layerGroup();
    points.forEach(point => {{
      const color = healthToColor(point.health);
      L.circleMarker([point.lat, point.lon], {{
        radius: 3,
        fillColor: color,
        color: '#333',
        weight: 1,
        opacity: 0.8,
        fillOpacity: 0.7
      }}).bindPopup(`
        <strong>Índice de Saúde: ${{point.health.toFixed(2)}}%</strong><br/>
        Vídeo: ${{point.video_name}}<br/>
        Frame: ${{point.frame_index}}<br/>
        Timestamp: ${{point.timestamp}}<br/>
        Coordenadas: ${{point.lat.toFixed(6)}}, ${{point.lon.toFixed(6)}}
      `).addTo(pointsLayer);
    }});
    
    // Adicionar layers iniciais
    heatmapLayer.addTo(map);
    gridLayer.addTo(map);
    
    // Controles
    const overlays = {{
      "Heatmap": heatmapLayer,
      "Grid Interpolado": gridLayer,
      "Pontos Originais": pointsLayer
    }};
    
    L.control.layers(baseLayers, overlays, {{ collapsed: false }}).addTo(map);
    
    // Event listeners para controles
    document.getElementById('showHeatmap').addEventListener('change', function(e) {{
      if (e.target.checked) heatmapLayer.addTo(map);
      else map.removeLayer(heatmapLayer);
    }});
    
    document.getElementById('showGrid').addEventListener('change', function(e) {{
      if (e.target.checked) gridLayer.addTo(map);
      else map.removeLayer(gridLayer);
    }});
    
    document.getElementById('showPoints').addEventListener('change', function(e) {{
      if (e.target.checked) pointsLayer.addTo(map);
      else map.removeLayer(pointsLayer);
    }});
    
    document.getElementById('heatmapRadius').addEventListener('input', function(e) {{
      const radius = parseInt(e.target.value);
      document.getElementById('radiusValue').textContent = radius;
      map.removeLayer(heatmapLayer);
      heatmapLayer = L.heatLayer(heatmapData, {{
        radius: radius,
        blur: radius * 0.6,
        maxZoom: 18,
        gradient: {{
          0.0: 'red',
          0.5: 'yellow',
          1.0: 'green'
        }},
        opacity: 0.6
      }});
      if (document.getElementById('showHeatmap').checked) {{
        heatmapLayer.addTo(map);
      }}
    }});
    
    document.getElementById('gridOpacity').addEventListener('input', function(e) {{
      const opacity = parseInt(e.target.value) / 100;
      document.getElementById('opacityValue').textContent = parseInt(e.target.value);
      gridLayer.eachLayer(function(layer) {{
        layer.setStyle({{
          opacity: opacity,
          fillOpacity: opacity
        }});
      }});
    }});
  </script>
</body>
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
    
    # Carregar dados
    print("📖 Carregando dados...")
    points = load_metadata_with_health(csv_path)
    
    if not points:
        print("❌ Nenhum ponto encontrado!")
        return
    
    print(f"   ✅ {len(points):,} pontos carregados")
    
    # Calcular bounds
    print("\n🗺️  Calculando área de voo...")
    bounds = calculate_bounds(points)
    print(f"   Latitude: {bounds['min_lat']:.6f} a {bounds['max_lat']:.6f}")
    print(f"   Longitude: {bounds['min_lon']:.6f} a {bounds['max_lon']:.6f}")
    
    # Estatísticas
    print("\n📊 Calculando estatísticas...")
    stats = calculate_statistics(points)
    print(f"   Saúde média: {stats['mean']:.2f}%")
    print(f"   Saúde mín/máx: {stats['min']:.2f}% / {stats['max']:.2f}%")
    
    # Criar grid interpolado
    print("\n🔢 Criando grid interpolado (isso pode levar alguns segundos)...")
    grid_points = create_interpolation_grid(points, grid_size=80)
    print(f"   ✅ Grid criado com {len(grid_points):,} células")
    
    # Gerar HTML
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

