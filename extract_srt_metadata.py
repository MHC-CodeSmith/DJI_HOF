#!/usr/bin/env python3
"""
Extração de Metadados de Arquivos SRT DJI
Extrai informações de GPS, câmera e timestamps de arquivos .SRT do DJI Mini 4 Pro
Gera CSVs formatados para QGIS/ArcGIS
"""

import re
import os
import csv
from pathlib import Path
from typing import Dict, List, Optional

def parse_metadata_line(line: str) -> Dict[str, Optional[str]]:
    """
    Extrai metadados de uma linha que contém [key: value] pairs.
    Retorna um dicionário com todos os campos encontrados.
    """
    metadata = {}
    
    # Padrões regex para cada campo
    patterns = {
        'iso': r'\[iso:\s*(\d+)\]',
        'shutter': r'\[shutter:\s*([^\]]+)\]',
        'fnum': r'\[fnum:\s*([\d.]+)\]',
        'ev': r'\[ev:\s*([-\d]+)\]',
        'color_md': r'\[color_md:\s*([^\]]+)\]',
        'focal_len': r'\[focal_len:\s*([\d.]+)\]',
        'latitude': r'\[latitude:\s*([\d.]+)\]',
        'longitude': r'\[longitude:\s*([\d.]+)\]',
        'rel_alt': r'\[rel_alt:\s*([\d.]+)',
        'abs_alt': r'abs_alt:\s*([\d.]+)\]',
        'ct': r'\[ct:\s*(\d+)\]'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, line)
        if match:
            metadata[key] = match.group(1)
        else:
            metadata[key] = None
    
    return metadata

def extract_frame_info(lines: List[str]) -> Optional[Dict[str, str]]:
    """
    Extrai informações de um bloco de frame do SRT.
    Retorna None se não conseguir extrair dados válidos.
    """
    frame_data = {
        'frame_index': None,
        'timestamp': None,
        'iso': None,
        'shutter': None,
        'aperture': None,
        'ev': None,
        'color_mode': None,
        'focal_length': None,
        'latitude': None,
        'longitude': None,
        'relative_altitude': None,
        'absolute_altitude': None,
        'color_temperature': None
    }
    
    # Procura por FrameCnt
    for line in lines:
        frame_match = re.search(r'FrameCnt:\s*(\d+)', line)
        if frame_match:
            frame_data['frame_index'] = frame_match.group(1)
            break
    
    # Procura por timestamp (formato: YYYY-MM-DD HH:MM:SS.mmm)
    timestamp_pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})'
    for line in lines:
        ts_match = re.search(timestamp_pattern, line)
        if ts_match:
            frame_data['timestamp'] = ts_match.group(1)
            break
    
    # Procura por linha com metadados [key: value]
    metadata_line = None
    for line in lines:
        if '[' in line and ':' in line and ']' in line:
            metadata_line = line
            break
    
    if not metadata_line:
        return None
    
    # Extrai todos os metadados
    metadata = parse_metadata_line(metadata_line)
    
    # Mapeia os campos
    frame_data['iso'] = metadata.get('iso')
    frame_data['shutter'] = metadata.get('shutter')
    frame_data['aperture'] = metadata.get('fnum')
    frame_data['ev'] = metadata.get('ev')
    frame_data['color_mode'] = metadata.get('color_md')
    frame_data['focal_length'] = metadata.get('focal_len')
    frame_data['latitude'] = metadata.get('latitude')
    frame_data['longitude'] = metadata.get('longitude')
    frame_data['relative_altitude'] = metadata.get('rel_alt')
    frame_data['absolute_altitude'] = metadata.get('abs_alt')
    frame_data['color_temperature'] = metadata.get('ct')
    
    # Valida se tem pelo menos frame_index e coordenadas
    if frame_data['frame_index'] and frame_data['latitude'] and frame_data['longitude']:
        return frame_data
    
    return None

def parse_srt_file(srt_path: Path) -> List[Dict[str, str]]:
    """
    Parse um arquivo SRT completo e retorna lista de dicionários com metadados.
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Divide em blocos de frames (cada bloco é separado por linha em branco dupla)
    blocks = re.split(r'\n\s*\n', content)
    
    all_frames = []
    
    for block in blocks:
        if not block.strip():
            continue
        
        lines = block.strip().split('\n')
        frame_data = extract_frame_info(lines)
        
        if frame_data:
            all_frames.append(frame_data)
    
    return all_frames

def write_csv(data: List[Dict[str, str]], output_path: Path):
    """
    Escreve os dados extraídos em formato CSV para QGIS/ArcGIS.
    """
    if not data:
        print(f"⚠️  Nenhum dado encontrado para escrever em {output_path}")
        return
    
    # Ordena por frame_index
    data_sorted = sorted(data, key=lambda x: int(x.get('frame_index', 0)))
    
    # Define os campos na ordem desejada
    fieldnames = [
        'frame_index',
        'timestamp',
        'latitude',
        'longitude',
        'relative_altitude',
        'absolute_altitude',
        'iso',
        'shutter',
        'aperture',
        'ev',
        'color_mode',
        'focal_length',
        'color_temperature'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for frame in data_sorted:
            # Prepara os dados garantindo que todos os campos existam
            row = {field: frame.get(field, '') for field in fieldnames}
            writer.writerow(row)
    
    print(f"✅ CSV criado: {output_path} ({len(data_sorted)} frames)")

def process_all_srt_files(base_dir: Path):
    """
    Processa todos os arquivos .SRT no diretório e cria estrutura organizada.
    """
    base_dir = Path(base_dir)
    
    # Encontra todos os arquivos SRT
    srt_files = list(base_dir.rglob('*.SRT')) + list(base_dir.rglob('*.srt'))
    
    if not srt_files:
        print(f"⚠️  Nenhum arquivo .SRT encontrado em {base_dir}")
        return
    
    print(f"📁 Encontrados {len(srt_files)} arquivo(s) .SRT\n")
    
    # Cria diretório de saída principal
    output_base = base_dir / 'extracted_metadata'
    output_base.mkdir(exist_ok=True)
    
    processed_count = 0
    
    for srt_file in sorted(srt_files):
        print(f"🔄 Processando: {srt_file.name}")
        
        try:
            # Extrai o nome base (sem extensão)
            base_name = srt_file.stem
            
            # Cria pasta para este arquivo
            file_output_dir = output_base / base_name
            file_output_dir.mkdir(exist_ok=True)
            
            # Processa o arquivo SRT
            frames_data = parse_srt_file(srt_file)
            
            if frames_data:
                # Cria arquivo CSV
                csv_path = file_output_dir / f'{base_name}_metadata.csv'
                write_csv(frames_data, csv_path)
                
                # Cria um resumo em texto
                summary_path = file_output_dir / f'{base_name}_summary.txt'
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"Arquivo: {srt_file.name}\n")
                    f.write(f"Total de frames extraídos: {len(frames_data)}\n")
                    f.write(f"\nPrimeiros 5 frames:\n")
                    f.write("-" * 80 + "\n")
                    
                    for i, frame in enumerate(frames_data[:5], 1):
                        f.write(f"\nFrame {i}:\n")
                        f.write(f"  Frame Index: {frame.get('frame_index')}\n")
                        f.write(f"  Timestamp: {frame.get('timestamp')}\n")
                        f.write(f"  Latitude: {frame.get('latitude')}\n")
                        f.write(f"  Longitude: {frame.get('longitude')}\n")
                        f.write(f"  Altitude Relativa: {frame.get('relative_altitude')} m\n")
                        f.write(f"  ISO: {frame.get('iso')}\n")
                        f.write(f"  Focal Length: {frame.get('focal_length')} mm\n")
                
                print(f"   ✅ {len(frames_data)} frames extraídos\n")
                processed_count += 1
            else:
                print(f"   ⚠️  Nenhum frame válido encontrado\n")
                
        except Exception as e:
            print(f"   ❌ Erro ao processar {srt_file.name}: {str(e)}\n")
    
    print(f"\n{'='*80}")
    print(f"✅ Processamento concluído!")
    print(f"   {processed_count}/{len(srt_files)} arquivos processados com sucesso")
    print(f"   Arquivos extraídos em: {output_base}")
    print(f"{'='*80}")

if __name__ == '__main__':
    # Diretório base do projeto
    project_dir = Path(__file__).parent
    
    print("🚀 Iniciando extração de metadados dos arquivos SRT DJI\n")
    print(f"📂 Diretório: {project_dir}\n")
    
    process_all_srt_files(project_dir)

