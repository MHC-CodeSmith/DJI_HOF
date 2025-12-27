#!/usr/bin/env python3
"""
Processa TODOS os vídeos automaticamente para calcular índice de saúde.
Encontra todos os CSVs de metadados e processa cada vídeo correspondente.
"""

import os
from pathlib import Path
from add_health_index import (
    load_or_train_model,
    find_video_in_folder,
    load_metadata_rows,
    write_metadata_with_health,
    compute_health_from_frame,
)
import cv2
from sklearn.linear_model import LogisticRegression


PROJECT_ROOT = Path(__file__).parent
FLIGHT_VIDEO_FOLDER = PROJECT_ROOT / "DJI_20251114105612_0065_D"
METADATA_BASE_DIR = PROJECT_ROOT / "extracted_metadata"


def find_all_metadata_csvs():
    """Encontra todos os CSVs de metadados que ainda precisam ser processados."""
    csv_files = []
    
    if not METADATA_BASE_DIR.exists():
        print(f"❌ Diretório de metadados não encontrado: {METADATA_BASE_DIR}")
        return csv_files
    
    # Procura por todos os CSVs de metadados
    for subdir in METADATA_BASE_DIR.iterdir():
        if not subdir.is_dir():
            continue
        
        csv_file = subdir / f"{subdir.name}_metadata.csv"
        if csv_file.exists():
            # Verifica se já foi processado
            health_csv = subdir / f"{subdir.name}_metadata_with_health.csv"
            if not health_csv.exists():
                csv_files.append(csv_file)
            else:
                print(f"⏭️  Já processado: {csv_file.name}")
    
    return sorted(csv_files)


def find_video_by_name(video_name: str):
    """Encontra o vídeo MP4 correspondente pelo nome base."""
    video_file = FLIGHT_VIDEO_FOLDER / f"{video_name}.MP4"
    if video_file.exists():
        return video_file
    
    # Tenta variações
    for ext in [".mp4", ".MP4", ".mov", ".MOV", ".avi", ".AVI"]:
        video_file = FLIGHT_VIDEO_FOLDER / f"{video_name}{ext}"
        if video_file.exists():
            return video_file
    
    return None


def process_single_video(model: LogisticRegression, csv_path: Path):
    """Processa um único vídeo e seu CSV de metadados."""
    video_name = csv_path.parent.name
    print(f"\n{'='*80}")
    print(f"🎬 Processando: {video_name}")
    print(f"{'='*80}")
    
    # Encontra o vídeo correspondente
    video_path = find_video_by_name(video_name)
    if not video_path:
        print(f"⚠️  Vídeo não encontrado para {video_name}. Pulando...")
        return False
    
    print(f"📹 Vídeo: {video_path.name}")
    print(f"📄 CSV: {csv_path.name}")
    
    # Carrega metadados
    try:
        fieldnames, rows = load_metadata_rows(csv_path)
    except Exception as e:
        print(f"❌ Erro ao carregar CSV: {e}")
        return False
    
    # Abre o vídeo
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ Não foi possível abrir o vídeo: {video_path}")
        return False
    
    print(f"[INFO] Calculando índices de saúde para {len(rows)} frames...")
    total_rows = len(rows)
    processed_frames = 0
    
    try:
        for i, row in enumerate(rows):
            ret, frame = cap.read()
            if not ret:
                print(f"[WARN] Frames do vídeo acabaram na linha {i+1}/{total_rows}. Parando.")
                break
            
            # Calcula saúde do frame
            healthy_ratio, unhealthy_ratio, status = compute_health_from_frame(frame, model)
            
            row["health_ratio_percent"] = f"{healthy_ratio:.2f}"
            row["unhealthy_ratio_percent"] = f"{unhealthy_ratio:.2f}"
            row["health_status"] = status
            
            processed_frames += 1
            if (i + 1) % 100 == 0 or (i + 1) == total_rows:
                print(f"  → {i+1}/{total_rows} frames processados ({processed_frames*100/total_rows:.1f}%)")
        
    except Exception as e:
        print(f"❌ Erro durante processamento: {e}")
        cap.release()
        return False
    
    finally:
        cap.release()
    
    # Salva o CSV com health
    output_csv = csv_path.with_name(csv_path.stem + "_with_health.csv")
    write_metadata_with_health(fieldnames, rows[:processed_frames], output_csv)
    
    print(f"✅ {processed_frames} frames processados com sucesso!")
    return True


def main():
    print("🚀 Processamento em Lote - Índice de Saúde da Vegetação")
    print("=" * 80)
    print(f"📂 Projeto: {PROJECT_ROOT}")
    print(f"📂 Pasta de vídeos: {FLIGHT_VIDEO_FOLDER}")
    print(f"📂 Diretório de metadados: {METADATA_BASE_DIR}")
    print("=" * 80)
    
    # Encontra todos os CSVs que precisam ser processados
    csv_files = find_all_metadata_csvs()
    
    if not csv_files:
        print("\n✅ Todos os vídeos já foram processados ou nenhum CSV encontrado!")
        return
    
    print(f"\n📋 Encontrados {len(csv_files)} vídeo(s) para processar:")
    for csv_file in csv_files:
        print(f"   - {csv_file.parent.name}")
    
    # Carrega ou treina o modelo (uma vez para todos)
    print("\n🤖 Carregando modelo...")
    model = load_or_train_model()
    
    # Processa cada vídeo
    success_count = 0
    failed_count = 0
    
    for i, csv_path in enumerate(csv_files, 1):
        print(f"\n[{i}/{len(csv_files)}] ", end="")
        if process_single_video(model, csv_path):
            success_count += 1
        else:
            failed_count += 1
    
    # Resumo final
    print("\n" + "=" * 80)
    print("📊 RESUMO DO PROCESSAMENTO")
    print("=" * 80)
    print(f"✅ Sucesso: {success_count} vídeo(s)")
    print(f"❌ Falhas: {failed_count} vídeo(s)")
    print(f"📁 Total: {len(csv_files)} vídeo(s)")
    print("=" * 80)
    
    if success_count > 0:
        print(f"\n🎉 {success_count} vídeo(s) processado(s) com sucesso!")


if __name__ == "__main__":
    main()

