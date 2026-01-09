import cv2
import numpy as np
import joblib
from pathlib import Path
import sys

# Add src to path if running directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.models.definitions import compute_features
from src.models.inference import load_model_and_scaler

def generate_visual_proof(video_path, output_dir, frame_idx=350):
    """
    Generates visual proof of the model's performance.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading model...")
    clf, scaler = load_model_and_scaler()
    
    print(f"Opening video: {video_path}")
    # Force FFMPEG backend
    cap = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
    
    frame = None
    if not cap.isOpened():
        print("Warning: Could not open video with FFMPEG backend.")
        # Try to find a specific JPG in the same folder as a fallback
        parent_dir = video_path.parent
        print(f"Looking for JPGs in {parent_dir}...")
        
        # Hardcoded fallback found in file listing
        fallback_jpg = parent_dir / "DJI_20251114085409_0052_D.JPG"
        
        if fallback_jpg.exists():
            print(f"Found fallback image: {fallback_jpg}")
            frame = cv2.imread(str(fallback_jpg))
        else:
             # Try globbing just in case
             jpgs = list(parent_dir.glob("*.JPG"))
             if jpgs:
                frame = cv2.imread(str(jpgs[0]))
             else:
                print(f"Error: Could not open video and fallback {fallback_jpg} not found.")
                return
    else:
        # Skip to desired frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("Error: Could not read frame from video.")
            return

    if frame is None:
         print("Error: No frame loaded.")
         return
    
    # Save Original
    original_path = output_dir / "proof_1_original.jpg"
    cv2.imwrite(str(original_path), frame)
    print(f"Saved original frame to {original_path}")
    
    # ---------------------------------------------------------
    # Process Frame
    # ---------------------------------------------------------
    print("Processing frame...")
    # Resize for speed (optional, but good for demo if full 4k is too slow)
    # We will stick to original resolution for "Proof" quality if possible,
    # but the model might be trained on smaller patches.
    # The pixelwise model is size-agnostic, but let's resize to a manageable HD if it's 4K
    h, w = frame.shape[:2]
    if w > 1920:
         frame = cv2.resize(frame, (1920, 1080))
         h, w = frame.shape[:2]
         
    # Compute features
    feats = compute_features(frame)
    
    # Scale
    if scaler:
        feats = scaler.transform(feats)
        
    # Predict
    print("Predicting...")
    # 0 = Unhealthy, 1 = Healthy
    preds_flat = clf.predict(feats)
    
    # Reshape back to image
    mask_indices = preds_flat.reshape(h, w)
    
    # ---------------------------------------------------------
    # Create Visualizations
    # ---------------------------------------------------------
    
    # 1. Binary Mask (Black/White)
    # Healthy (1) -> White (255)
    # Unhealthy (0) -> Black (0)
    mask_img = (mask_indices * 255).astype(np.uint8)
    mask_path = output_dir / "proof_2_mask_bw.jpg"
    cv2.imwrite(str(mask_path), mask_img)
    print(f"Saved binary mask to {mask_path}")
    
    # 2. Colored Mask (Green/Red)
    # Create a blank RGB image
    color_mask = np.zeros_like(frame)
    
    # Where mask is 1 (Healthy) -> Green (0, 255, 0)
    color_mask[mask_indices == 1] = [0, 255, 0]
    
    # Where mask is 0 (Unhealthy) -> Red (0, 0, 255)
    color_mask[mask_indices == 0] = [0, 0, 255]
    
    mask_color_path = output_dir / "proof_3_mask_color.jpg"
    cv2.imwrite(str(mask_color_path), color_mask)
    print(f"Saved color mask to {mask_color_path}")
    
    # 3. Overlay (Original + Transparent Mask)
    alpha = 0.4
    overlay = cv2.addWeighted(frame, 1 - alpha, color_mask, alpha, 0)
    
    overlay_path = output_dir / "proof_4_overlay.jpg"
    cv2.imwrite(str(overlay_path), overlay)
    print(f"Saved overlay to {overlay_path}")
    
    # 4. Side-by-Side Comparison (The Money Shot)
    # Stack horizontally
    combined = np.hstack((frame, overlay))
    combined_path = output_dir / "proof_5_comparison.jpg"
    cv2.imwrite(str(combined_path), combined)
    print(f"Saved comparison to {combined_path}")
    
    print("\n✅ Verification Generation Complete!")

if __name__ == "__main__":
    # Correct path including the flight folder
    VIDEO_FILE = PROJECT_ROOT / "datasets" / "flights" / "DJI_20251114105612_0065_D" / "DJI_20251114093134_0057_D.MP4"
    OUTPUT_LOC = PROJECT_ROOT / "proof_output"
    
    generate_visual_proof(VIDEO_FILE, OUTPUT_LOC)
