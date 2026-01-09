import cv2
import numpy as np
import joblib
import os
import sys
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Local imports
from src.models.definitions import compute_features

# Paths
PLANTVILLAGE_DIR = PROJECT_ROOT / "datasets" / "PlantVillage"
MODEL_PATH = PROJECT_ROOT / "data" / "models" / "pixelwise_sgd_classifier.pkl"
SCALER_PATH = PROJECT_ROOT / "data" / "models" / "pixelwise_scaler.pkl"

IMAGE_SIZE = (128, 128)
RANDOM_SEED = 42

def load_model_and_scaler(model_path):
    print(f"Loading model from {model_path}...")
    data = joblib.load(model_path)
    if isinstance(data, dict) and 'clf' in data:
        clf = data['clf']
        scaler = data.get('scaler')
    else:
        clf = data
        scaler = None 
        # try loading separate scaler if needed, but training script saves together now
    return clf, scaler

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

def evaluate_on_image_set(clf, scaler, image_paths, image_labels):
    y_true = []
    y_pred = []
    
    print(f"Evaluating on {len(image_paths)} images...")
    
    for i, (p, lab) in enumerate(zip(image_paths, image_labels)):
        img = cv2.imread(p)
        if img is None:
            continue
        img = cv2.resize(img, IMAGE_SIZE)
        feats = compute_features(img)
        
        if scaler:
            feats = scaler.transform(feats)
            
        preds = clf.predict(feats)
        
        # Image-level decision: Mean pixel health > 0.5
        healthy_ratio = np.mean(preds == 1)
        pred_label = 1 if healthy_ratio >= 0.5 else 0
        
        y_true.append(lab)
        y_pred.append(pred_label)
        
        if i % 100 == 0:
            print(f"Processed {i}/{len(image_paths)}")
            
    return y_true, y_pred

def main():
    if not MODEL_PATH.exists():
        print(f"Error: Model file not found at {MODEL_PATH}")
        return

    print("Listing ALL PlantVillage images...")
    paths, labels = list_plantvillage_images(PLANTVILLAGE_DIR)
    
    if not paths:
        print("Error: No images found.")
        return
        
    # Replicate the split logic from train_model.py to isolate the TEST set
    # p_train, p_temp, y_train, y_temp = train_test_split(paths, labels, test_size=0.3, stratify=labels, random_state=RANDOM_SEED)
    # p_val, p_test, y_val, y_test = train_test_split(p_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=RANDOM_SEED)
    
    print("Splitting dataset to isolate TEST set (15%)...")
    _, p_temp, _, y_temp = train_test_split(paths, labels, test_size=0.3, stratify=labels, random_state=RANDOM_SEED)
    _, p_test, _, y_test = train_test_split(p_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=RANDOM_SEED)
    
    print(f"Test Set Size: {len(p_test)} images")
    
    clf, scaler = load_model_and_scaler(MODEL_PATH)
    
    # Run Evaluation
    y_true, y_pred = evaluate_on_image_set(clf, scaler, p_test, y_test)
    
    # Report
    acc = accuracy_score(y_true, y_pred)
    report = classification_report(y_true, y_pred, target_names=["Unhealthy", "Healthy"])
    cm = confusion_matrix(y_true, y_pred)
    
    print("\n" + "="*40)
    print(f"FINAL TEST RESULTS (N={len(y_true)})")
    print("="*40)
    print(f"ACCURACY: {acc*100:.2f}%")
    print("-" * 40)
    print("CLASSIFICATION REPORT:")
    print(report)
    print("-" * 40)
    print("CONFUSION MATRIX:")
    print(cm)
    print("="*40)

    # Save validation document
    with open("validation_results.txt", "w") as f:
        f.write(f"Validation Metrics for PlantVillage Test Set\n")
        f.write(f"Accuracy: {acc*100:.2f}%\n\n")
        f.write(f"Classification Report:\n{report}\n")

if __name__ == "__main__":
    main()
