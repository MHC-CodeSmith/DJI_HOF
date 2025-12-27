#!/usr/bin/env python3
"""
Validation Script #2
Health over time for a full video

Usage:
    python3 validate_health_video.py [video_name]
    
    Se não especificar video_name, escolhe um aleatório.
"""

import cv2
import numpy as np
from pathlib import Path
import joblib
import random
import sys
from statistics import mean

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  matplotlib não disponível. Gráfico não será gerado.")


PROJECT_ROOT = Path(__file__).parent
MODEL_PATH = PROJECT_ROOT / "models" / "health_model.pkl"
VIDEO_FOLDER = PROJECT_ROOT / "DJI_20251114105612_0065_D"


def load_random_video():
    """Carrega um vídeo aleatório da pasta de voos."""
    exts = (".mp4", ".avi", ".mov", ".mkv")
    vids = [p for p in VIDEO_FOLDER.iterdir() 
            if p.suffix.lower() in exts and p.is_file()]
    
    if not vids:
        raise FileNotFoundError(f"Nenhum vídeo encontrado em {VIDEO_FOLDER}")
    
    return random.choice(vids)


def find_video_by_name(video_name: str):
    """Encontra vídeo pelo nome (com ou sem extensão)."""
    # Remove extensão se presente
    video_name_base = Path(video_name).stem
    
    exts = [".mp4", ".MP4", ".mov", ".MOV", ".avi", ".AVI", ".mkv"]
    
    for ext in exts:
        video_path = VIDEO_FOLDER / f"{video_name_base}{ext}"
        if video_path.exists():
            return video_path
    
    return None


def compute_health(frame, model):
    """
    Computa o índice de saúde para um frame.
    Retorna: imagem blendada, porcentagem saudável, porcentagem não saudável.
    """
    # Redimensiona para processamento
    frame_disp = cv2.resize(frame, (512, 512))
    
    # Separa canais
    b, g, r = cv2.split(frame_disp.astype("float32"))
    
    # Calcula índices de vegetação
    VARI = (g - r) / (g + r - b + 1e-5)
    ExG = 2 * g - r - b
    TGI = -0.5 * ((190 * (r - g)) - (120 * (r - b)))
    
    # Prepara features
    feats = np.stack([VARI.flatten(), ExG.flatten(), TGI.flatten()], axis=1)
    
    # Predição do modelo
    preds = model.predict(feats).reshape(VARI.shape)
    
    # Calcula porcentagens
    healthy = np.sum(preds == 1) / preds.size * 100.0
    unhealthy = 100.0 - healthy
    
    # Cria mapa de saúde
    health_map = np.zeros_like(frame_disp)
    health_map[preds == 1] = [0, 255, 0]  # Verde para saudável
    health_map[preds == 0] = [0, 0, 255]  # Vermelho para não saudável
    
    # Blend: 60% original + 40% mapa de saúde
    blended = cv2.addWeighted(
        frame_disp.astype("uint8"), 0.6,
        health_map.astype("uint8"), 0.4, 0
    )
    
    return blended, healthy, unhealthy


def plot_health_over_time(health_values, video_name):
    """Plota gráfico de saúde ao longo do tempo."""
    if not MATPLOTLIB_AVAILABLE:
        print("\n⚠️  matplotlib não disponível. Gráfico não será exibido.")
        return
    
    plt.figure(figsize=(12, 6))
    
    # Plota linha de saúde
    plt.plot(health_values, label="Saúde (%)", color="green", linewidth=2)
    
    # Linha de média
    avg_health = mean(health_values)
    plt.axhline(y=avg_health, color='orange', linestyle='--', 
                label=f'Média: {avg_health:.2f}%', linewidth=2)
    
    plt.ylim(0, 100)
    plt.xlabel("Amostra de Frame (a cada 5 frames)", fontsize=12)
    plt.ylabel("Porcentagem de Saúde (%)", fontsize=12)
    plt.title(f"Índice de Saúde ao Longo do Tempo\n{video_name}", fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=11)
    
    # Adiciona estatísticas no gráfico
    stats_text = f"Mín: {min(health_values):.1f}% | "
    stats_text += f"Máx: {max(health_values):.1f}% | "
    stats_text += f"Mediana: {sorted(health_values)[len(health_values)//2]:.1f}%"
    
    plt.figtext(0.5, 0.02, stats_text, ha='center', fontsize=10, 
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.show()


def main():
    print("🔍 Validação Visual - Saúde ao Longo do Tempo (Vídeo)")
    print("=" * 80)
    
    # Verifica se o modelo existe
    if not MODEL_PATH.exists():
        print(f"❌ Modelo não encontrado: {MODEL_PATH}")
        print("   Execute primeiro: python3 add_health_index.py")
        sys.exit(1)
    
    # Verifica se a pasta de vídeos existe
    if not VIDEO_FOLDER.exists():
        print(f"❌ Pasta de vídeos não encontrada: {VIDEO_FOLDER}")
        sys.exit(1)
    
    # Carrega modelo
    print("🤖 Carregando modelo...")
    model = joblib.load(MODEL_PATH)
    print("✅ Modelo carregado!")
    
    # Carrega vídeo
    if len(sys.argv) > 1:
        video_name = sys.argv[1]
        print(f"\n📹 Procurando vídeo: {video_name}")
        video_path = find_video_by_name(video_name)
        if not video_path:
            print(f"❌ Vídeo não encontrado: {video_name}")
            sys.exit(1)
    else:
        print("\n📹 Carregando vídeo aleatório...")
        video_path = load_random_video()
    
    print(f"   ✅ Vídeo: {video_path.name}")
    
    # Abre vídeo
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"❌ Erro ao abrir vídeo: {video_path}")
        sys.exit(1)
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"   📊 Total de frames: {total_frames}")
    print(f"   ⏱️  FPS: {fps:.2f}")
    print(f"   ⏱️  Duração: {total_frames/fps:.1f} segundos")
    
    # Processa vídeo
    print("\n🎬 Processando vídeo...")
    print("   Pressione 'q' durante a visualização para pular para o gráfico")
    print("   Ou aguarde o vídeo terminar\n")
    
    health_over_time = []
    frame_idx = 0
    sample_rate = 5  # Processa 1 a cada 5 frames para ser mais rápido
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Processa apenas alguns frames (para velocidade)
        if frame_idx % sample_rate == 0:
            blended, healthy, unhealthy = compute_health(frame, model)
            health_over_time.append(healthy)
            
            # Adiciona informações na imagem
            info_text = f"Frame: {frame_idx} | Saude: {healthy:.1f}%"
            cv2.putText(blended, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(blended, "Pressione 'q' para pular", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            cv2.imshow("Health Map Stream - Video Validation", blended)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\n⏭️  Pulando para gráfico...")
                break
        
        frame_idx += 1
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Estatísticas
    if not health_over_time:
        print("\n❌ Nenhum frame processado!")
        sys.exit(1)
    
    print(f"\n📊 Estatísticas:")
    print(f"   Total de amostras: {len(health_over_time)}")
    print(f"   Saúde mínima: {min(health_over_time):.2f}%")
    print(f"   Saúde máxima: {max(health_over_time):.2f}%")
    print(f"   Saúde média: {mean(health_over_time):.2f}%")
    print(f"   Desvio padrão: {np.std(health_over_time):.2f}%")
    
    # Plota gráfico
    if MATPLOTLIB_AVAILABLE:
        print("\n📈 Gerando gráfico...")
        plot_health_over_time(health_over_time, video_path.stem)
    else:
        print("\n⚠️  Instale matplotlib para ver o gráfico:")
        print("   pip install matplotlib")
    
    print("\n✅ Validação concluída!")


if __name__ == "__main__":
    main()

