import cv2
import os
import numpy as np

def get_selective_mean_frame(img):
    img_f = img.astype(np.float32)
    up = np.roll(img_f, -1, axis=0)
    down = np.roll(img_f, 1, axis=0)
    left = np.roll(img_f, -1, axis=1)
    right = np.roll(img_f, 1, axis=1)
    
    neighbors = [up, down, left, right]
    mean_all = (up + down + left + right) / 4

    distances = [np.linalg.norm(n - mean_all, axis=2) for n in neighbors]
    max_dist_idx = np.argmax(np.stack(distances, axis=0), axis=0)
    
    sum_neighbors = up + down + left + right
    final_avg = np.zeros_like(img_f)
    
    for i in range(4):
        mask = (max_dist_idx == i)
        final_avg[mask] = (sum_neighbors[mask] - neighbors[i][mask]) / 3
        
    return final_avg.astype(np.uint8)

def process_video():
    video_path = input("Video File Path: ").strip('"')
    if not os.path.exists(video_path):
        print("Error: Video not found.")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    save_dir = os.path.dirname(video_path)
    output_path = os.path.join(save_dir, 'processed_pixel_video.mp4')
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    y, x = np.indices((height, width))
    checker_mask = (x + y) % 2 == 0

    print(f"Processing {total_frames} frames...")

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        smart_avg = get_selective_mean_frame(frame)
        
        processed_frame = smart_avg.copy()

        if frame_count % 2 == 0:

            processed_frame[checker_mask] = frame[checker_mask]
        else:

            processed_frame[~checker_mask] = frame[~checker_mask]

        out.write(processed_frame)
        frame_count += 1
        
        if frame_count % 10 == 0:
            print(f"Progress: {frame_count}/{total_frames} frames", end="\r")

    cap.release()
    out.release()
    print(f"\nDone! Video saved at: {output_path}")

if __name__ == "__main__":
    process_video()