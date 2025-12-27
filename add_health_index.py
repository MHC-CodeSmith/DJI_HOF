#!/usr/bin/env python3
"""
add_health_index.py

1) Treina (ou carrega) um modelo de "plant health" usando o dataset:
   Dataset_Hipolito_drone/

2) Abre o vídeo da pasta do voo:
   DJI_20251114105612_0065_D/

3) Lê o CSV de metadados extraídos do SRT:
   extracted_metadata/DJI_20251114091511_0054_D/DJI_20251114091511_0054_D_metadata.csv

4) Para cada linha (frame) do CSV, calcula um índice de saúde:
   - health_ratio_percent
   - unhealthy_ratio_percent
   - health_status (Healthy / Moderate / Unhealthy)

5) Gera um novo CSV com os campos extras:
   ..._metadata_with_health.csv

Dependências (já usadas no seu código antigo):
- opencv-python
- numpy
- scikit-learn
- matplotlib (não é usada aqui, pode ignorar)
- joblib
"""

import os
from pathlib import Path
import random
import csv

import cv2
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import joblib


# --------------------------------------------------------------------------------------
# CONFIGURAÇÕES PRINCIPAIS
# --------------------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent

# Datasets usados para treinar o modelo
DATASET_HIPOLITO = PROJECT_ROOT / "Dataset_Hipolito_drone"
DATASET_PLANTVILLAGE = PROJECT_ROOT / "PlantVillage"

# Onde salvar/carregar o modelo treinado
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODELS_DIR / "health_model.pkl"

# Voo a ser processado (pasta do vídeo bruto, na raiz do projeto)
FLIGHT_VIDEO_FOLDER = PROJECT_ROOT / "DJI_20251114105612_0065_D"

# CSV de metadados já extraído pelo seu script de SRT
METADATA_CSV = (
    PROJECT_ROOT
    / "extracted_metadata"
    / "DJI_20251114091511_0054_D"
    / "DJI_20251114091511_0054_D_metadata.csv"
)


# --------------------------------------------------------------------------------------
# FUNÇÕES DO MODELO (TREINO E FEATURE EXTRACTION)
# --------------------------------------------------------------------------------------

def collect_dataset_images(dataset_path: Path):
    """Percorre a pasta do dataset e coleta todos os caminhos de imagens."""
    all_images = []
    for root, dirs, files in os.walk(dataset_path):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                all_images.append(Path(root) / file)
    return all_images


def extract_frames_from_video(video_path: Path, num_frames: int = 50, frame_interval: int = None):
    """
    Extrai frames de um vídeo MP4.
    
    Args:
        video_path: Caminho para o vídeo
        num_frames: Número máximo de frames para extrair
        frame_interval: Intervalo entre frames (None = calcular automaticamente)
    
    Returns:
        Lista de frames (arrays numpy)
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames == 0:
        cap.release()
        return []
    
    # Calcula intervalo se não especificado
    if frame_interval is None:
        frame_interval = max(1, total_frames // num_frames)
    
    frames = []
    frame_idx = 0
    
    while len(frames) < num_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Pula frames baseado no intervalo
        if frame_idx % frame_interval == 0:
            frames.append(frame)
        
        frame_idx += 1
        
        # Evita loop infinito
        if frame_idx >= total_frames:
            break
    
    cap.release()
    return frames


def collect_video_frames(dataset_path: Path, frames_per_video: int = 50):
    """
    Coleta frames de todos os vídeos MP4 no dataset.
    Retorna lista de frames (numpy arrays).
    """
    all_frames = []
    video_files = []
    
    # Encontra todos os vídeos MP4
    for root, dirs, files in os.walk(dataset_path):
        for file in files:
            if file.lower().endswith((".mp4", ".mov", ".avi")):
                video_files.append(Path(root) / file)
    
    print(f"[INFO] Encontrados {len(video_files)} vídeo(s) para extrair frames...")
    
    for video_path in video_files:
        frames = extract_frames_from_video(video_path, num_frames=frames_per_video)
        all_frames.extend(frames)
        if frames:
            print(f"  → {video_path.name}: {len(frames)} frames extraídos")
    
    return all_frames


def is_healthy_from_path(img_path: Path):
    """
    Determina se uma imagem é healthy baseado no caminho.
    Para PlantVillage: se a pasta contém 'healthy' = True
    """
    path_str = str(img_path).lower()
    # Verifica se está em uma pasta com 'healthy' no nome
    parts = img_path.parts
    for part in parts:
        if 'healthy' in part.lower():
            return True
    return False


def process_image_for_training(img, is_plantvillage, img_path=None):
    """
    Processa uma imagem para treinamento.
    Retorna features (X) e labels (y) para a imagem.
    """
    img = cv2.resize(img, (128, 128))
    b, g, r = cv2.split(img.astype("float32"))
    
    VARI = (g - r) / (g + r - b + 1e-5)
    ExG = 2 * g - r - b
    TGI = -0.5 * ((190 * (r - g)) - (120 * (r - b)))
    green_intensity = g / (r + g + b + 1e-5)
    
    VARI_f = VARI.flatten()
    ExG_f = ExG.flatten()
    TGI_f = TGI.flatten()
    green_f = green_intensity.flatten()
    
    # Gera labels baseado no tipo de dataset
    if is_plantvillage and img_paimage.pngth:
        # PlantVillage: usa nome da pasta
        is_healthy = is_healthy_from_path(img_path)
        labels = np.full(len(VARI_f), 1 if is_healthy else 0, dtype=int)
    else:
        # Dataset_Hipolito: usa intensidade de verde relativa
        median_val = np.median(green_f)
        labels = (green_f > median_val).astype(int)
    
    features = np.stack([VARI_f, ExG_f, TGI_f], axis=1)
    return features, labels


def train_health_model(dataset_paths: list):
    """
    Treina o modelo de Logistic Regression usando múltiplos datasets.
    
    - Usa imagens e frames de vídeo de múltiplos datasets
    - Extrai VARI, ExG, TGI por pixel
    - Para PlantVillage: usa nome da pasta para labels (healthy/unhealthy)
    - Para Dataset_Hipolito: extrai frames dos vídeos MP4 + usa intensidade de verde
    """
    all_training_data = []  # Lista de (image_array, is_plantvillage, img_path)
    
    # Coleta dados de todos os datasets
    for dataset_path in dataset_paths:
        if not dataset_path or not dataset_path.exists():
            print(f"[WARN] Dataset não encontrado: {dataset_path}, pulando...")
            continue
        
        is_plantvillage = "plantvillage" in str(dataset_path).lower()
        
        if is_plantvillage:
            # PlantVillage: coleta imagens estáticas
            images = collect_dataset_images(dataset_path)
            if images:
                for img_path in images:
                    img = cv2.imread(str(img_path))
                    if img is not None:
                        all_training_data.append((img, True, img_path))
                print(f"[INFO] Dataset {dataset_path.name}: {len(images)} imagens encontradas")
        else:
            # Dataset_Hipolito: extrai apenas POUCOS frames dos vídeos MP4 (para não sobrecarregar)
            print(f"[INFO] Extraindo alguns frames dos vídeos em {dataset_path.name}...")
            frames = collect_video_frames(dataset_path, frames_per_video=5)  # Apenas 5 frames por vídeo
            if frames:
                for frame in frames:
                    all_training_data.append((frame, False, None))
                print(f"[INFO] Dataset {dataset_path.name}: {len(frames)} frames extraídos de vídeos")
            
            # Também coleta imagens JPG/PNG se houver
            images = collect_dataset_images(dataset_path)
            if images:
                for img_path in images:
                    img = cv2.imread(str(img_path))
                    if img is not None:
                        all_training_data.append((img, False, None))
                print(f"[INFO] Dataset {dataset_path.name}: {len(images)} imagens estáticas encontradas")
    
    if not all_training_data:
        raise FileNotFoundError(
            "Nenhum dado encontrado nos datasets. "
            "Verifique os caminhos dos datasets."
        )
    
    total_items = len(all_training_data)
    print(f"[INFO] Total de {total_items} itens coletados (imagens + frames de vídeo).")
    
        # Separa cada dataset
    plantvillage_items = [item for item in all_training_data if item[1]]
    hipolito_items = [item for item in all_training_data if not item[1]]

    print(f"[INFO] Total PlantVillage encontrado: {len(plantvillage_items)} imagens")
    print(f"[INFO] Total Dataset_Hipolito encontrado: {len(hipolito_items)} frames/imagens")

    # Queremos TODO o PlantVillage
    selected_plantvillage = plantvillage_items

    # E apenas alguns poucos frames do Dataset Hipolito (para evitar confundir o modelo)
    NUM_HIPOLITO_SAMPLES = 20  # ajuste se quiser mais
    selected_hipolito = random.sample(
        hipolito_items,
        min(NUM_HIPOLITO_SAMPLES, len(hipolito_items))
    )

    print(f"[INFO] Usando {len(selected_plantvillage)} imagens do PlantVillage")
    print(f"[INFO] Usando {len(selected_hipolito)} frames do Dataset_Hipolito")

    selected_items = selected_plantvillage + selected_hipolito
    random.shuffle(selected_items)

    print(f"[INFO] Usando {num_plantvillage_samples} do PlantVillage e {num_hipolito_samples} do Dataset_Hipolito para treino.")
    print(f"[INFO] Total: {len(selected_items)} itens selecionados.")
    
    X = []
    y = []
    
    print(f"[INFO] Processando {len(selected_items)} itens...")
    for idx, (img, is_plantvillage, img_path) in enumerate(selected_items):
        if (idx + 1) % 50 == 0:
            print(f"  → Processando: {idx + 1}/{len(selected_items)}")
        
        features, labels = process_image_for_training(img, is_plantvillage, img_path)
        
        X.extend(features)
        y.extend(labels)
    
    X = np.array(X)
    y = np.array(y)
    print(f"[INFO] Amostras de pixels para treino: {len(X):,}")
    
    # Estatísticas dos labels
    healthy_count = np.sum(y == 1)
    unhealthy_count = np.sum(y == 0)
    print(f"[INFO] Distribuição: {healthy_count:,} saudáveis ({healthy_count*100/len(y):.1f}%), {unhealthy_count:,} não saudáveis ({unhealthy_count*100/len(y):.1f}%)")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"[INFO] Treinando modelo...")
    model = LogisticRegression(max_iter=1000, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"[INFO] Acurácia Logistic Regression: {acc*100:.2f}%")
    
    return model


def load_or_train_model() -> LogisticRegression:
    """
    Carrega o modelo de disco, se existir.
    Caso contrário, treina um novo modelo e salva em models/health_model.pkl.
    """
    MODELS_DIR.mkdir(exist_ok=True)

    if MODEL_PATH.exists():
        print(f"[INFO] Carregando modelo existente de {MODEL_PATH}")
        model = joblib.load(MODEL_PATH)
        return model

    print("[INFO] Nenhum modelo salvo encontrado. Treinando novo modelo...")
    print(f"[INFO] Datasets: {DATASET_HIPOLITO.name}, {DATASET_PLANTVILLAGE.name}")
    
    # Lista de datasets para treinar
    dataset_paths = [DATASET_HIPOLITO, DATASET_PLANTVILLAGE]
    
    model = train_health_model(dataset_paths)
    joblib.dump(model, MODEL_PATH)
    print(f"[INFO] Modelo salvo em {MODEL_PATH}")
    return model


def compute_health_from_frame(frame, model: LogisticRegression):
    """
    Calcula o índice de saúde para um frame:
    - Redimensiona
    - Extrai VARI, ExG, TGI
    - Prediz por pixel (0/1)
    - Retorna:
      health_ratio_percent, unhealthy_ratio_percent, status_str
    """
    # Ajusta o tamanho para reduzir custo
    frame_resized = cv2.resize(frame, (256, 256))
    b, g, r = cv2.split(frame_resized.astype("float32"))

    VARI = (g - r) / (g + r - b + 1e-5)
    ExG = 2 * g - r - b
    TGI = -0.5 * ((190 * (r - g)) - (120 * (r - b)))

    features = np.stack([VARI.flatten(), ExG.flatten(), TGI.flatten()], axis=1)
    preds = model.predict(features).reshape(VARI.shape)

    healthy_ratio = float(np.sum(preds == 1)) / preds.size * 100.0
    unhealthy_ratio = 100.0 - healthy_ratio

    if healthy_ratio > 60:
        status = "Healthy"
    elif healthy_ratio > 40:
        status = "Moderate"
    else:
        status = "Unhealthy"

    return healthy_ratio, unhealthy_ratio, status


# --------------------------------------------------------------------------------------
# PROCESSAMENTO DO VÍDEO + CSV
# --------------------------------------------------------------------------------------

def find_video_in_folder(folder: Path):
    """Procura um arquivo de vídeo (mp4/mov/avi) dentro da pasta do voo."""
    if not folder.exists():
        raise FileNotFoundError(f"Pasta de vídeo não encontrada: {folder}")

    candidates = []
    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() in [".mp4", ".mov", ".avi", ".mkv"]:
            candidates.append(file)

    if not candidates:
        raise FileNotFoundError(f"Nenhum vídeo encontrado em {folder}")

    # pega o primeiro (pode ajustar se quiser escolher outro)
    video_path = candidates[0]
    print(f"[INFO] Vídeo selecionado: {video_path.name}")
    return video_path


def load_metadata_rows(csv_path: Path):
    """Lê o CSV de metadados e retorna (fieldnames, rows)."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV de metadados não encontrado: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    print(f"[INFO] Linhas de metadados carregadas: {len(rows)}")
    return fieldnames, rows


def write_metadata_with_health(original_fieldnames, rows, output_path: Path):
    """Grava um novo CSV com os campos de health adicionados."""
    new_fields = [
        "health_ratio_percent",
        "unhealthy_ratio_percent",
        "health_status",
    ]
    fieldnames = original_fieldnames + [f for f in new_fields if f not in original_fieldnames]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"[INFO] Novo CSV com health salvo em: {output_path}")


def annotate_flight_with_health(model: LogisticRegression):
    """
    Faz o casamento vídeo <-> CSV e calcula o health por frame.

    Estratégia simples:
    - Assume que o CSV está ordenado por frame_index.
    - Lê um frame do vídeo para cada linha do CSV, na mesma ordem.
      (não usamos o número exato do frame_index para seek, apenas sequência).
    """
    video_path = find_video_in_folder(FLIGHT_VIDEO_FOLDER)
    fieldnames, rows = load_metadata_rows(METADATA_CSV)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Não foi possível abrir o vídeo: {video_path}")

    print("[INFO] Calculando índices de saúde por frame...")
    total_rows = len(rows)
    processed_frames = 0

    for i, row in enumerate(rows):
        ret, frame = cap.read()
        if not ret:
            print(f"[WARN] Acabaram os frames do vídeo (linha {i}). Parando.")
            break

        healthy_ratio, unhealthy_ratio, status = compute_health_from_frame(frame, model)

        row["health_ratio_percent"] = f"{healthy_ratio:.2f}"
        row["unhealthy_ratio_percent"] = f"{unhealthy_ratio:.2f}"
        row["health_status"] = status

        processed_frames += 1
        if (i + 1) % 50 == 0 or (i + 1) == total_rows:
            print(f"  -> {i+1}/{total_rows} linhas processadas")

    cap.release()

    # Salva novo CSV com sufixo
    output_csv = METADATA_CSV.with_name(METADATA_CSV.stem + "_with_health.csv")
    write_metadata_with_health(fieldnames, rows[:processed_frames], output_csv)


# --------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------

def main():
    print("🚀 add_health_index.py iniciado")
    print(f"📂 Projeto: {PROJECT_ROOT}")
    print(f"📂 Datasets para treino: {DATASET_HIPOLITO.name}, {DATASET_PLANTVILLAGE.name}")
    print(f"📂 Pasta do voo (vídeo): {FLIGHT_VIDEO_FOLDER}")
    print(f"📄 CSV de metadados: {METADATA_CSV}")
    print("-" * 80)

    # 1) Carrega ou treina modelo
    model = load_or_train_model()

    # 2) Aplica modelo ao voo/CSV
    annotate_flight_with_health(model)

    print("\n✅ Processo concluído com sucesso.")


if __name__ == "__main__":
    main()
