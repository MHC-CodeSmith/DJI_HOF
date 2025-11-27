#!/usr/bin/env python3
"""
Adiciona um índice dummy de saúde da vegetação (0-100%) ao CSV consolidado.
O índice é gerado de forma controlada para demonstração.
"""

import csv
import random
import math
from pathlib import Path
from statistics import mean


def generate_health_index(latitude, longitude, relative_altitude, frame_index, video_name):
    """
    Gera um índice dummy de saúde (0-100%) baseado em padrões espaciais.
    Usa latitude/longitude para criar zonas com diferentes níveis de saúde.
    """
    # Semente baseada na posição para consistência
    seed = int(abs(latitude * 10000) + abs(longitude * 10000))
    random.seed(seed)
    
    # Cria padrões espaciais (zona central mais saudável, bordas menos saudáveis)
    # Centro da área de voo aproximado (pode ajustar)
    center_lat = 50.329
    center_lon = 11.939
    
    # Distância do centro
    lat_diff = abs(latitude - center_lat)
    lon_diff = abs(longitude - center_lon)
    distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111000  # aproximado em metros
    
    # Base health: diminui com distância do centro
    base_health = 85.0 - (distance / 50.0)  # Máx ~85% no centro, diminui com distância
    
    # Variação aleatória controlada
    variation = random.gauss(0, 8)  # variação gaussiana
    
    # Efeito da altitude (maior altitude = melhor iluminação = potencialmente mais saudável)
    altitude_bonus = 0
    if relative_altitude:
        altitude_bonus = min(5.0, (relative_altitude - 1.5) * 2.0)
    
    # Cálculo final
    health = base_health + variation + altitude_bonus
    
    # Garante que está entre 0 e 100
    health = max(0.0, min(100.0, health))
    
    return round(health, 2)


def add_health_index_to_csv(input_csv, output_csv):
    """Adiciona coluna health_index ao CSV."""
    rows = []
    
    print(f"📖 Lendo: {input_csv}")
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        if not fieldnames:
            print("❌ Erro: CSV vazio ou inválido")
            return
        
        # Adiciona health_index aos fieldnames
        new_fieldnames = list(fieldnames) + ['health_index']
        
        for row in reader:
            try:
                lat = float(row.get('latitude', 0) or 0)
                lon = float(row.get('longitude', 0) or 0)
                rel_alt = None
                if row.get('relative_altitude'):
                    try:
                        rel_alt = float(row.get('relative_altitude'))
                    except (ValueError, TypeError):
                        pass
                
                frame_idx = row.get('frame_index', '0')
                video = row.get('video_name', 'unknown')
                
                # Gera índice de saúde
                health = generate_health_index(lat, lon, rel_alt, frame_idx, video)
                row['health_index'] = str(health)
                
                rows.append(row)
                
            except Exception as e:
                print(f"⚠️  Erro ao processar linha: {e}")
                continue
    
    print(f"💾 Escrevendo: {output_csv}")
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Estatísticas
    health_values = [float(row['health_index']) for row in rows if row.get('health_index')]
    if health_values:
        print(f"\n✅ Índice de saúde adicionado!")
        print(f"   Total de registros: {len(rows):,}")
        print(f"   Saúde mínima: {min(health_values):.2f}%")
        print(f"   Saúde máxima: {max(health_values):.2f}%")
        print(f"   Saúde média: {mean(health_values):.2f}%")
        print(f"   Arquivo salvo: {output_csv}")


def main():
    base_dir = Path(__file__).parent
    input_csv = base_dir / "extracted_metadata" / "all_metadata_consolidated.csv"
    output_csv = base_dir / "extracted_metadata" / "all_metadata_with_health.csv"
    
    if not input_csv.exists():
        print(f"❌ Arquivo não encontrado: {input_csv}")
        print("   Execute primeiro extract_srt_metadata.py e create_consolidated_csv.py")
        return
    
    print("🚀 Adicionando índice dummy de saúde ao CSV consolidado\n")
    add_health_index_to_csv(input_csv, output_csv)
    print("\n✅ Processamento concluído!")


if __name__ == '__main__':
    main()

