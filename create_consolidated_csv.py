#!/usr/bin/env python3
"""
Cria um arquivo CSV consolidado combinando todos os metadados extraídos.
Útil para análises globais de todos os voos.
Usa apenas bibliotecas padrão do Python (sem dependências externas).
"""

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def read_csv_file(csv_path):
    """Lê um arquivo CSV e retorna lista de dicionários."""
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def safe_float(value):
    """Converte valor para float de forma segura."""
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None

def create_consolidated_csv():
    """
    Cria um arquivo CSV único com todos os metadados de todos os vídeos.
    Adiciona uma coluna 'video_name' para identificar a origem.
    """
    base_dir = Path(__file__).parent / 'extracted_metadata'
    
    # Encontra todos os arquivos CSV de metadados
    csv_files = list(base_dir.glob('*/*_metadata.csv'))
    
    if not csv_files:
        print("⚠️  Nenhum arquivo CSV encontrado em extracted_metadata/")
        return
    
    print(f"📁 Encontrados {len(csv_files)} arquivo(s) CSV\n")
    
    all_rows = []
    video_stats = defaultdict(lambda: {'count': 0, 'latitudes': [], 'longitudes': [], 
                                       'altitudes': [], 'timestamps': []})
    
    for csv_file in sorted(csv_files):
        # Extrai o nome do vídeo da pasta pai
        video_name = csv_file.parent.name
        print(f"🔄 Processando: {video_name}")
        
        try:
            # Carrega o CSV
            rows = read_csv_file(csv_file)
            
            # Adiciona coluna video_name e coleta estatísticas
            for row in rows:
                row['video_name'] = video_name
                all_rows.append(row)
                
                # Coleta estatísticas
                video_stats[video_name]['count'] += 1
                lat = safe_float(row.get('latitude'))
                lon = safe_float(row.get('longitude'))
                alt = safe_float(row.get('relative_altitude'))
                
                if lat:
                    video_stats[video_name]['latitudes'].append(lat)
                if lon:
                    video_stats[video_name]['longitudes'].append(lon)
                if alt:
                    video_stats[video_name]['altitudes'].append(alt)
                if row.get('timestamp'):
                    video_stats[video_name]['timestamps'].append(row['timestamp'])
            
            print(f"   ✅ {len(rows)} frames adicionados")
            
        except Exception as e:
            print(f"   ❌ Erro ao processar {csv_file}: {str(e)}")
    
    if not all_rows:
        print("\n⚠️  Nenhum dado foi carregado!")
        return
    
    # Define ordem das colunas (video_name no início)
    fieldnames = ['video_name', 'frame_index', 'timestamp', 'latitude', 'longitude',
                  'relative_altitude', 'absolute_altitude', 'iso', 'shutter', 
                  'aperture', 'ev', 'color_mode', 'focal_length', 'color_temperature']
    
    # Ordena por vídeo e frame_index
    def sort_key(row):
        video = row.get('video_name', '')
        try:
            frame_idx = int(row.get('frame_index', 0))
        except (ValueError, TypeError):
            frame_idx = 0
        return (video, frame_idx)
    
    all_rows.sort(key=sort_key)
    
    # Salva o arquivo consolidado
    output_file = base_dir / 'all_metadata_consolidated.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in all_rows:
            # Garante que todas as colunas existam
            output_row = {col: row.get(col, '') for col in fieldnames}
            writer.writerow(output_row)
    
    print(f"\n✅ Arquivo consolidado criado: {output_file}")
    print(f"   Total de frames: {len(all_rows):,}")
    print(f"   Total de vídeos: {len(video_stats)}")
    
    # Estatísticas por vídeo
    print("\n📊 Estatísticas por vídeo:")
    print("-" * 80)
    
    # Calcula estatísticas globais
    all_lats = []
    all_lons = []
    all_alts = []
    
    # Cria arquivo de estatísticas
    stats_file = base_dir / 'statistics_summary.txt'
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("Estatísticas Consolidadas dos Metadados Extraídos\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total de frames: {len(all_rows):,}\n")
        f.write(f"Total de vídeos: {len(video_stats)}\n\n")
        f.write("Frames por vídeo:\n")
        f.write("-" * 80 + "\n")
        
        for video in sorted(video_stats.keys()):
            stats = video_stats[video]
            count = stats['count']
            f.write(f"{video}: {count:,} frames\n")
            print(f"{video}: {count:,} frames")
            
            # Coleta dados globais
            all_lats.extend(stats['latitudes'])
            all_lons.extend(stats['longitudes'])
            all_alts.extend(stats['altitudes'])
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("\nEstatísticas Detalhadas por Vídeo:\n")
        f.write("-" * 80 + "\n")
        
        for video in sorted(video_stats.keys()):
            stats = video_stats[video]
            f.write(f"\n{video}:\n")
            f.write(f"  Frames: {stats['count']}\n")
            
            if stats['latitudes']:
                f.write(f"  Latitude: {min(stats['latitudes']):.6f} a {max(stats['latitudes']):.6f}\n")
            if stats['longitudes']:
                f.write(f"  Longitude: {min(stats['longitudes']):.6f} a {max(stats['longitudes']):.6f}\n")
            if stats['altitudes']:
                avg_alt = sum(stats['altitudes']) / len(stats['altitudes'])
                f.write(f"  Altitude Relativa: {min(stats['altitudes']):.2f} a {max(stats['altitudes']):.2f} m (média: {avg_alt:.2f} m)\n")
            if stats['timestamps']:
                f.write(f"  Timestamp inicial: {min(stats['timestamps'])}\n")
                f.write(f"  Timestamp final: {max(stats['timestamps'])}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("\nEstatísticas Globais:\n")
        f.write("-" * 80 + "\n")
        
        if all_lats:
            f.write(f"Latitude mínima: {min(all_lats):.6f}\n")
            f.write(f"Latitude máxima: {max(all_lats):.6f}\n")
        if all_lons:
            f.write(f"Longitude mínima: {min(all_lons):.6f}\n")
            f.write(f"Longitude máxima: {max(all_lons):.6f}\n")
        if all_alts:
            avg_alt_global = sum(all_alts) / len(all_alts)
            f.write(f"\nAltitude Relativa:\n")
            f.write(f"  Mínima: {min(all_alts):.2f} m\n")
            f.write(f"  Máxima: {max(all_alts):.2f} m\n")
            f.write(f"  Média: {avg_alt_global:.2f} m\n")
    
    print(f"\n✅ Estatísticas salvas em: {stats_file}")
    print("\n" + "=" * 80)
    print("✅ Processamento concluído!")

if __name__ == '__main__':
    print("🚀 Criando CSV consolidado de todos os metadados\n")
    create_consolidated_csv()

