import cv2
import numpy as np
import joblib
from pathlib import Path

# Local import
try:
    from src.models.definitions import compute_features
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from src.models.definitions import compute_features

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "data" / "models" / "pixelwise_sgd_classifier.pkl"
SCALER_PATH = PROJECT_ROOT / "data" / "models" / "pixelwise_scaler.pkl"

def load_model_and_scaler(model_path=MODEL_PATH, scaler_path=SCALER_PATH):
    """
    Loads the trained model and scaler.
    """
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found at {model_path}. Please run src/models/train_model.py first.")
    
    # Check if they are saved together or separately
    # The training script saves them together in the final step: joblib.dump({'clf': clf, 'scaler': scaler}, MODEL_PATH)
    data = joblib.load(model_path)
    
    if isinstance(data, dict) and 'clf' in data:
        clf = data['clf']
        scaler = data.get('scaler') # might be separate
    else:
        # Fallback if structure is different
        clf = data
        scaler = joblib.load(scaler_path) if scaler_path.exists() else None
        
    return clf, scaler

def predict_frame(frame, clf, scaler, resize_dim=(128, 128)):
    """
    Predicts health index for a single frame.
    
    Args:
        frame: BGR image (numpy array).
        clf: Trained classifier.
        scaler: Fitted scaler (optional, but recommended).
        resize_dim: Tuple (width, height) to resize before processing (speed optimization).
        
    Returns:
        healthy_ratio: Percentage of healthy pixels (0-100).
        unhealthy_ratio: Percentage of unhealthy pixels (0-100).
        status: String "Healthy", "Moderate", or "Unhealthy".
        mask: Numpy array of shape (height, width) with 0=Unhealthy, 1=Healthy.
    """
    original_h, original_w = frame.shape[:2]
    if resize_dim:
        frame_proc = cv2.resize(frame, resize_dim)
    else:
        frame_proc = frame
        
    feats = compute_features(frame_proc)
    
    if scaler:
        feats = scaler.transform(feats)
        
    # Predict pixel-wise
    # 0 = unhealthy, 1 = healthy
    preds = clf.predict(feats)
    
    # Reshape preds back to image shape (H, W)
    # compute_features flattens the image, so we know the size corresponds to resize_dim or original frame
    if resize_dim:
        w, h = resize_dim
    else:
        h, w = frame.shape[:2]
        
    mask = preds.reshape((h, w))
    
    # Calculate ratios
    total_pixels = preds.size
    healthy_pixels = np.sum(preds == 1)
    
    healthy_ratio = (healthy_pixels / total_pixels) * 100.0
    unhealthy_ratio = 100.0 - healthy_ratio
    
    # Determine status
    if healthy_ratio > 60:
        status = "Healthy"
    elif healthy_ratio > 40:
        status = "Moderate"
    else:
        status = "Unhealthy"
        
    return healthy_ratio, unhealthy_ratio, status, mask
