import av
import cv2
import numpy as np

container = av.open("rtmp://127.0.0.1:1998/live/drone")

# Get stream configuration
stream = container.streams.video[0]
width = stream.width
height = stream.height
fps = float(stream.average_rate)
if fps == 0: fps = 30.0

# Setup VideoWriter to save MP4
save_path = "livestream_record.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(save_path, fourcc, fps, (width, height))
print(f"Saving recording to {save_path}...")

for frame in container.decode(video=0):
    img = frame.to_ndarray(format="bgr24")
    
    # Write frame to file
    out.write(img)
    
    cv2.imshow("DJI Stream", img)

    if cv2.waitKey(1) == 27:
        break

out.release()

