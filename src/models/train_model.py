import os
import cv2
import numpy as np
import random
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import time
from pathlib import Path

# Local import
try:
    from src.models.definitions import compute_features
except ImportError:
    # Fallback if running directly from src/models
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from src.models.definitions import compute_features

# Configuration
# Assuming script runs from src/models or project root. 
# We'll use absolute paths based on project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

PLANTVILLAGE_DIR = PROJECT_ROOT / "datasets" / "PlantVillage"
DRONE_DIR = PROJECT_ROOT / "datasets" / "Dataset_Hipolito_drone"
MODEL_DIR = PROJECT_ROOT / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "pixelwise_sgd_classifier.pkl"
SCALER_PATH = MODEL_DIR / "pixelwise_scaler.pkl"

IMAGE_SIZE = (128, 128)   # resize to reduce per-image pixels (tune as needed)
FRAME_SKIP = 5            # use one frame every FRAME_SKIP frames from videos
RANDOM_SEED = 42

# Training control
MAX_EPOCHS = 20
TARGET_VAL_ACC = 0.80
BATCH_PIXELS_LIMIT = None   # None => use all pixels from each image/frame

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

def list_plantvillage_images(root):
    paths = []
    labels = []
    for dirpath, dirs, files in os.walk(root):
        if dirpath == root:
            continue
        folder = os.path.basename(dirpath).lower()
        is_healthy = "healthy" in folder
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                paths.append(os.path.join(dirpath, f))
                labels.append(1 if is_healthy else 0)
    return paths, labels

def list_drone_frames(video_dir, frame_skip=FRAME_SKIP, max_videos=None):
    frame_sources = []
    videos = []
    for root, dirs, files in os.walk(video_dir):
        for f in files:
            if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                videos.append(os.path.join(root, f))
    if max_videos is not None:
        videos = videos[:max_videos]
    # Represent as (video_path, frame_index) pairs will be generated on-the-fly to avoid storing frames
    return videos


def sample_or_all(feats, labels, limit=BATCH_PIXELS_LIMIT):
    if limit is None or feats.shape[0] <= limit:
        return feats, labels
    idx = np.random.choice(feats.shape[0], size=limit, replace=False)
    return feats[idx], labels[idx]

def fit_scaler_incremental(scaler, image_paths, max_images=None):
    count = 0
    for p in image_paths:
        img = cv2.imread(p)
        if img is None:
            continue
        img = cv2.resize(img, IMAGE_SIZE)
        feats = compute_features(img)
        feats_s, _ = sample_or_all(feats, np.zeros(feats.shape[0]), limit=None)
        scaler.partial_fit(feats_s.astype(np.float64))
        count += 1
        if max_images is not None and count >= max_images:
            break
        if count % 500 == 0:
            print(f"[INFO] Scaler fitted on {count} images...")
    return scaler

def iterate_train_epoch(clf, scaler, train_image_paths, train_labels, videos, epoch_num):
    start = time.time()
    total_samples = 0
    # Shuffle at image level
    idxs = np.arange(len(train_image_paths))
    np.random.shuffle(idxs)
    for i in idxs:
        p = train_image_paths[i]
        label = train_labels[i]
        img = cv2.imread(p)
        if img is None:
            continue
        img = cv2.resize(img, IMAGE_SIZE)
        feats = compute_features(img)
        labels = np.full((feats.shape[0],), label, dtype=np.uint8)
        feats_s, labels_s = sample_or_all(feats, labels)
        X = scaler.transform(feats_s).astype(np.float64)
        clf.partial_fit(X, labels_s.astype(np.int64), classes=np.array([0,1], dtype=np.int64))
        total_samples += X.shape[0]
    # Optionally also include some video frames each epoch (sampled)
    for v in videos:
        cap = cv2.VideoCapture(v)
        if not cap.isOpened():
            continue
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if frame_idx % FRAME_SKIP != 0:
                continue
            frame_r = cv2.resize(frame, IMAGE_SIZE)
            feats = compute_features(frame_r)
            # weak labeling by per-frame median (unsupervised)
            b,g,r = cv2.split(frame_r.astype("float32"))
            green_intensity = g / (r + g + b + 1e-6)
            median_val = np.median(green_intensity.flatten())
            labels = (green_intensity.flatten() > median_val).astype(np.uint8)
            feats_s, labels_s = sample_or_all(feats, labels)
            X = scaler.transform(feats_s).astype(np.float64)
            clf.partial_fit(X, labels_s.astype(np.int64), classes=np.array([0,1], dtype=np.int64))
            total_samples += X.shape[0]
            # limit number of frames per video per epoch to avoid long runs (tune/remove if desired)
            # here we sample up to 50 frames per video per epoch
            if frame_idx > FRAME_SKIP * 50:
                break
        cap.release()
    elapsed = time.time() - start
    print(f"[INFO] Epoch {epoch_num} trained on ~{total_samples:,} pixel samples in {elapsed:.1f}s")
    return clf

def evaluate_on_image_set(clf, scaler, image_paths, image_labels, max_images=None):
    y_true = []
    y_pred = []
    count = 0
    for p, lab in zip(image_paths, image_labels):
        img = cv2.imread(p)
        if img is None:
            continue
        img = cv2.resize(img, IMAGE_SIZE)
        feats = compute_features(img)
        X = scaler.transform(feats)
        preds = clf.predict(X)
        # image-level decision: proportion of healthy pixels > 0.5 => image healthy
        healthy_ratio = np.mean(preds == 1)
        pred_label = 1 if healthy_ratio >= 0.5 else 0
        y_true.append(lab)
        y_pred.append(pred_label)
        count += 1
        if max_images is not None and count >= max_images:
            break
    acc = accuracy_score(y_true, y_pred) if y_true else 0.0
    return acc

def main():
    print("[INFO] Listing PlantVillage images...")
    paths, labels = list_plantvillage_images(PLANTVILLAGE_DIR)
    if not paths:
        raise RuntimeError("No PlantVillage images found.")
    print(f"[INFO] Found {len(paths)} PlantVillage images.")
    # split image-level
    p_train, p_temp, y_train, y_temp = train_test_split(paths, labels, test_size=0.3, stratify=labels, random_state=RANDOM_SEED)
    p_val, p_test, y_val, y_test = train_test_split(p_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=RANDOM_SEED)
    print(f"[INFO] Train/Val/Test images: {len(p_train)}/{len(p_val)}/{len(p_test)}")

    # list videos
    videos = list_drone_frames(DRONE_DIR)

    # build incremental scaler
    scaler = StandardScaler()
    print("[INFO] Fitting scaler incrementally on training images (one-pass)...")
    scaler = fit_scaler_incremental(scaler, p_train)
    joblib.dump(scaler, SCALER_PATH)
    print(f"[INFO] Scaler saved to {SCALER_PATH}")

    # initialize classifier
    clf = SGDClassifier(loss='log_loss', max_iter=1, tol=None, learning_rate='optimal', random_state=RANDOM_SEED)
    # perform one dummy partial_fit to initialize classes if needed
    clf.partial_fit(np.zeros((1,3), dtype=np.float64), np.array([0], dtype=np.int64), classes=np.array([0,1], dtype=np.int64))

    best_val = 0.0
    for epoch in range(1, MAX_EPOCHS+1):
        clf = iterate_train_epoch(clf, scaler, p_train, y_train, videos, epoch)
        # evaluate
        val_acc = evaluate_on_image_set(clf, scaler, p_val, y_val)
        test_acc = evaluate_on_image_set(clf, scaler, p_test, y_test, max_images=200)  # quick sample
        print(f"[INFO] After epoch {epoch}: val_acc={val_acc*100:.2f}%, test_sample_acc={test_acc*100:.2f}%")
        if val_acc > best_val:
            best_val = val_acc
            joblib.dump({'clf': clf}, MODEL_PATH)
            print(f"[INFO] New best model saved (val_acc={best_val*100:.2f}%) to {MODEL_PATH}")
        if val_acc >= TARGET_VAL_ACC:
            print(f"[OK] Target validation accuracy reached: {val_acc*100:.2f}%")
            break

    print(f"[DONE] Best validation accuracy: {best_val*100:.2f}%")
    # final save (classifier + scaler)
    joblib.dump({'clf': clf, 'scaler': scaler}, MODEL_PATH)
    print(f"[INFO] Final model+scaler saved to {MODEL_PATH}")

if __name__ == "__main__":
    main()
