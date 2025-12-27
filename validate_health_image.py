#!/usr/bin/env python3
"""
Validation Script #1
Visual check: Original vs Health Map side-by-side

Usage:
    python3 validate_health_image.py
"""

import cv2
import numpy as np
from pathlib import Path
import joblib
import random
import sys

PROJECT_ROOT = Path(__file__).parent
MODEL_PATH = PROJECT_ROOT / "models" / "health_model.pkl"
DATASET_PATH = PROJECT_ROOT / "Dataset_Hipolito_drone"


def load_random_image():
    """Carrega uma imagem aleatória do dataset."""
    exts = (".jpg", ".jpeg", ".png")
    imgs = [p for p in DATASET_PATH.rglob("*") if p.suffix.lower() in exts and p.is_file()]
    
    if not imgs:
        raise FileNotFoundError(f"Nenhuma imagem encontrada em {DATASET_PATH}")
    
    return random.choice(imgs)


def compute_health_map(frame, model):
    """
    Computa o mapa de saúde para um frame.
    Retorna imagem blendada mostrando áreas saudáveis (verde) e não saudáveis (vermelho).
    """
    # Redimensiona para processamento mais rápido
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
    
    # Cria mapa de saúde
    health_map = np.zeros_like(frame_disp)
    health_map[preds == 1] = [0, 255, 0]  # Verde para saudável
    health_map[preds == 0] = [0, 0, 255]  # Vermelho para não saudável
    
    # Blend: 60% original + 40% mapa de saúde
    blended = cv2.addWeighted(
        frame_disp.astype("uint8"), 0.6,
        health_map.astype("uint8"), 0.4, 0
    )
    
    return blended, health_map


def main():
    print("🔍 Validação Visual - Imagem Original vs Mapa de Saúde")
    print("=" * 80)
    
    # Verifica se o modelo existe
    if not MODEL_PATH.exists():
        print(f"❌ Modelo não encontrado: {MODEL_PATH}")
        print("   Execute primeiro: python3 add_health_index.py")
        sys.exit(1)
    
    # Verifica se o dataset existe
    if not DATASET_PATH.exists():
        print(f"❌ Dataset não encontrado: {DATASET_PATH}")
        sys.exit(1)
    
    # Carrega modelo
    print("🤖 Carregando modelo...")
    model = joblib.load(MODEL_PATH)
    print("✅ Modelo carregado!")
    
    # Carrega imagem aleatória
    print("\n📷 Carregando imagem aleatória do dataset...")
    img_path = load_random_image()
    print(f"   ✅ Imagem: {img_path.name}")
    
    frame = cv2.imread(str(img_path))
    if frame is None:
        print(f"❌ Erro ao carregar imagem: {img_path}")
        sys.exit(1)
    
    # Calcula mapa de saúde
    print("\n🧮 Calculando mapa de saúde...")
    blended, health_map = compute_health_map(frame, model)
    
    # Prepara visualização lado a lado
    original_resized = cv2.resize(frame, (512, 512))
    
    # Combina imagens horizontalmente
    combined = cv2.hconcat([original_resized, blended])
    
    # Adiciona labels
    cv2.putText(combined, "Original", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(combined, "Mapa de Saude (Verde=Saudavel, Vermelho=Nao Saudavel)", 
                (522, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Mostra resultado
    print("\n🖼️  Abrindo janela de visualização...")
    print("   Pressione qualquer tecla para fechar")
    
    cv2.imshow("Original (Esquerda) | Mapa de Saude (Direita)", combined)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print("\n✅ Validação concluída!")


if __name__ == "__main__":
    main()


