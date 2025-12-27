import cv2
import numpy as np
import os
import random
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# -----------------------------
# Step 0: Dataset Path
# -----------------------------
dataset_path = r"D:\VIT\HoF\ACADEMICS\APPLIED ROBOTICS\Drone_project\Dataset_Hipolito_drone"

all_images = []
all_videos = []

for root, dirs, files in os.walk(dataset_path):
    for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            all_images.append(os.path.join(root, file))
        elif file.lower().endswith(('.mp4', '.avi', '.mov')):
            all_videos.append(os.path.join(root, file))

if not all_images and not all_videos:
    raise FileNotFoundError("No images or videos found in your dataset folder!")

# -----------------------------
# Step 1: Feature Extraction & Model Training
# -----------------------------
X = []
y = []

num_train_images = min(50, len(all_images))
for img_path in random.sample(all_images, num_train_images):
    img = cv2.imread(img_path)
    if img is None:
        continue
    img = cv2.resize(img, (128, 128))
    b, g, r = cv2.split(img.astype('float32'))

    VARI = (g - r) / (g + r - b + 1e-5)
    ExG = 2 * g - r - b
    TGI = -0.5 * ((190 * (r - g)) - (120 * (r - b)))
    green_intensity = g / (r + g + b + 1e-5)

    VARI_f = VARI.flatten()
    ExG_f = ExG.flatten()
    TGI_f = TGI.flatten()
    green_f = green_intensity.flatten()

    median_val = np.median(green_f)
    labels = (green_f > median_val).astype(int)

    X.extend(np.stack([VARI_f, ExG_f, TGI_f], axis=1))
    y.extend(labels)

X = np.array(X)
y = np.array(y)
print(f"[INFO] Model trained on {len(X)} pixel samples.")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = LogisticRegression(max_iter=500)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"[INFO] Logistic Regression Accuracy: {acc*100:.2f}%")

# -----------------------------
# Step 2: Random Selection of Image or Video
# -----------------------------
choice_type = random.choice(['image', 'video'])
print(f"[INFO] Randomly selected {choice_type} for processing.")

if choice_type == 'image' and all_images:
    file_path = random.choice(all_images)
elif choice_type == 'video' and all_videos:
    file_path = random.choice(all_videos)
else:
    file_path = random.choice(all_images + all_videos)

# -----------------------------
# Step 3: Function to Process a Frame
# -----------------------------
def process_frame(frame, model):
    frame_disp = cv2.resize(frame, (512, 512))
    b, g, r = cv2.split(frame_disp.astype('float32'))

    VARI = (g - r) / (g + r - b + 1e-5)
    ExG = 2 * g - r - b
    TGI = -0.5 * ((190 * (r - g)) - (120 * (r - b)))

    features = np.stack([VARI.flatten(), ExG.flatten(), TGI.flatten()], axis=1)
    preds = model.predict(features).reshape(VARI.shape)

    health_map = np.zeros_like(frame_disp)
    health_map[preds == 1] = [0, 255, 0]   # Healthy
    health_map[preds == 0] = [0, 0, 255]   # Unhealthy

    blended = cv2.addWeighted(frame_disp.astype('uint8'), 0.6, health_map.astype('uint8'), 0.4, 0)

    healthy_ratio = np.sum(preds == 1) / preds.size * 100
    unhealthy_ratio = 100 - healthy_ratio
    status = "Healthy" if healthy_ratio > 60 else "Moderate" if healthy_ratio > 40 else "Unhealthy"

    return blended, healthy_ratio, unhealthy_ratio, status

# -----------------------------
# Step 4: Setup Matplotlib Interactive Mode
# -----------------------------
plt.ion()
fig, ax = plt.subplots(figsize=(5,5))
pie = None

# -----------------------------
# Step 5: Process Image
# -----------------------------
if file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
    img = cv2.imread(file_path)
    blended, healthy_ratio, unhealthy_ratio, status = process_frame(img, model)

    # Show original and processed side by side
    combined = cv2.hconcat([cv2.resize(img,(512,512)), blended])
    cv2.imshow("Original (Left) | Health Map (Right)", combined)

    # Update pie chart
    ax.clear()
    ax.pie([healthy_ratio, unhealthy_ratio],
           labels=['Healthy Area','Unhealthy Area'],
           colors=['#27ae60','#c0392b'],
           autopct='%1.1f%%', startangle=140, textprops={'fontsize':12})
    ax.set_title(f"Plant Health Status: {status}", fontsize=14)
    plt.draw()
    plt.pause(0.001)

    cv2.waitKey(0)
    cv2.destroyAllWindows()

# -----------------------------
# Step 6: Process Video
# -----------------------------
elif file_path.lower().endswith(('.mp4', '.avi', '.mov')):
    cap = cv2.VideoCapture(file_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = 0
    total_healthy = 0
    total_frames = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % 5 == 0:
            blended, healthy_ratio, unhealthy_ratio, status = process_frame(frame, model)
            total_healthy += healthy_ratio
            total_frames += 1

            # Show original and blended side by side
            combined = cv2.hconcat([cv2.resize(frame,(512,512)), blended])
            cv2.imshow("Original (Left) | Health Map (Right)", combined)

            # Update pie chart dynamically
            ax.clear()
            ax.pie([healthy_ratio, unhealthy_ratio],
                   labels=['Healthy Area','Unhealthy Area'],
                   colors=['#27ae60','#c0392b'],
                   autopct='%1.1f%%', startangle=140, textprops={'fontsize':12})
            ax.set_title(f"Plant Health Status: {status}", fontsize=14)
            plt.draw()
            plt.pause(0.001)

            if cv2.waitKey(100) & 0xFF == ord('q'):
                break
        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()
    healthy_ratio = total_healthy / total_frames
    unhealthy_ratio = 100 - healthy_ratio
    status = "Healthy" if healthy_ratio > 60 else "Moderate" if healthy_ratio > 40 else "Unhealthy"
    print(f"[INFO] Video: {os.path.basename(file_path)} -> {status} ({healthy_ratio:.1f}% healthy)")

# Keep final pie chart displayed
plt.ioff()
plt.show()
