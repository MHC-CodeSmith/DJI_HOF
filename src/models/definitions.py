import cv2
import numpy as np

def compute_features(img):
    """
    Computes pixel-wise vegetation indices (VARI, ExG, TGI) for an input image.
    
    Args:
        img: HxWx3 BGR uint8 image.
        
    Returns:
        d: (N, 3) float32 array where N = H*W. 
           Columns are [VARI, ExG, TGI].
    """
    # Create float32 copy for calculations
    img_f = img.astype("float32")
    b, g, r = cv2.split(img_f)
    
    eps = 1e-6
    
    # Visible Atmospherically Resistant Index
    VARI = (g - r) / (g + r - b + eps)
    
    # Excess Green
    ExG = 2 * g - r - b
    
    # Triangular Greenness Index
    # TGI = -0.5 * (190(R - G) - 120(R - B))
    TGI = -0.5 * ((190.0 * (r - g)) - (120.0 * (r - b)))
    
    # Stack features into (N, 3) array
    feat = np.stack([VARI.flatten(), ExG.flatten(), TGI.flatten()], axis=1)
    
    return feat
