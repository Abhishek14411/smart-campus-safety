"""
AI Smart Campus Safety & Monitoring System - Synthetic Campus Demo Video Generator
==================================================================================
Generates a 30-second realistic test video (videos/campus.mp4) featuring:
1. Normal walking pedestrians across campus pathways
2. A gathering of people testing Crowd Density classification
3. A pedestrian crossing into the designated Restricted Area
4. A running pedestrian exhibiting Rapid Movement anomalies
This ensures the system is 100% testable out-of-the-box on any machine without needing a physical camera.
"""

import os
import math
import random
from pathlib import Path
import cv2
import numpy as np

import config

def draw_pedestrian(frame, x, y, scale=1.0, color=(180, 140, 60), leg_phase=0.0):
    """
    Draws a stylized, realistic pedestrian silhouette with head, torso, arms, and walking legs
    that reliably triggers human detection models and provides clean visual fidelity.
    """
    h = int(90 * scale)
    w = int(32 * scale)
    head_r = int(12 * scale)
    
    # Coordinates
    head_cx = int(x)
    head_cy = int(y - h + head_r)
    
    # 1. Head
    cv2.circle(frame, (head_cx, head_cy), head_r, (210, 180, 150), -1, lineType=cv2.LINE_AA)
    # Hair / Cap
    cv2.ellipse(frame, (head_cx, head_cy - 2), (head_r, head_r - 2), 0, 180, 360, (50, 40, 30), -1, lineType=cv2.LINE_AA)
    
    # 2. Torso (Shirt/Jacket)
    torso_top = head_cy + head_r
    torso_bot = int(y - h * 0.42)
    cv2.rectangle(frame, (int(x - w * 0.45), torso_top), (int(x + w * 0.45), torso_bot), color, -1)
    
    # 3. Arms (animated based on phase)
    arm_swing = int(math.sin(leg_phase) * 12 * scale)
    cv2.line(frame, (int(x - w * 0.45), torso_top + 5), (int(x - w * 0.45 - arm_swing), torso_bot - 5), color, int(5 * scale), lineType=cv2.LINE_AA)
    cv2.line(frame, (int(x + w * 0.45), torso_top + 5), (int(x + w * 0.45 + arm_swing), torso_bot - 5), color, int(5 * scale), lineType=cv2.LINE_AA)
    
    # 4. Legs / Pants
    leg_swing = int(math.sin(leg_phase) * 16 * scale)
    hip_y = torso_bot
    foot_y = int(y)
    cv2.line(frame, (int(x - 5 * scale), hip_y), (int(x - 8 * scale + leg_swing), foot_y), (60, 60, 80), int(6 * scale), lineType=cv2.LINE_AA)
    cv2.line(frame, (int(x + 5 * scale), hip_y), (int(x + 8 * scale - leg_swing), foot_y), (60, 60, 80), int(6 * scale), lineType=cv2.LINE_AA)


def generate_campus_background(width=640, height=360):
    """
    Creates a detailed campus courtyard background with grass, stone paving, benches, and building facades.
    """
    bg = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Sky / Horizon
    bg[0:int(height * 0.35)] = (215, 195, 175)  # Light sky
    
    # Campus Buildings in background
    cv2.rectangle(bg, (20, 40), (220, int(height * 0.45)), (120, 110, 115), -1)
    cv2.rectangle(bg, (240, 20), (420, int(height * 0.45)), (95, 85, 100), -1)
    cv2.rectangle(bg, (440, 50), (620, int(height * 0.45)), (110, 100, 105), -1)
    
    # Building Windows
    for bx in [40, 80, 120, 160, 260, 300, 340, 380, 460, 500, 540, 580]:
        for by in [60, 90, 120]:
            cv2.rectangle(bg, (bx, by), (bx + 22, by + 20), (220, 230, 240), -1)
            cv2.rectangle(bg, (bx, by), (bx + 22, by + 20), (60, 60, 60), 1)

    # Courtyard Pavement
    bg[int(height * 0.35):] = (160, 165, 170)  # Concrete tiles
    
    # Walkway perspective grid
    for x in range(0, width + 100, 70):
        cv2.line(bg, (x - 80, int(height * 0.35)), (x + 80, height), (145, 150, 155), 1)
    for y in range(int(height * 0.35), height, 40):
        cv2.line(bg, (0, y), (width, y), (145, 150, 155), 1)
        
    # Campus Green lawn patches
    pts1 = np.array([[0, int(height * 0.55)], [140, int(height * 0.55)], [200, height], [0, height]], np.int32)
    cv2.fillPoly(bg, [pts1], (70, 130, 60))
    
    # Plant / Tree in lawn
    cv2.circle(bg, (70, int(height * 0.65)), 26, (50, 100, 40), -1)
    cv2.circle(bg, (85, int(height * 0.62)), 20, (60, 120, 45), -1)
    cv2.circle(bg, (60, int(height * 0.60)), 18, (45, 95, 35), -1)
    
    return bg


def create_demo_video(output_path=config.DEFAULT_VIDEO_PATH, duration_sec=25, fps=25):
    """
    Renders and exports the demo MP4 video.
    """
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    width = config.FRAME_WIDTH
    height = config.FRAME_HEIGHT
    total_frames = duration_sec * fps
    
    # Use MP4V or XVID codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    if not writer.isOpened():
        print(f"[DEMO GENERATOR ERROR] Failed to create video writer at: {output_path}")
        return False
        
    print(f"[DEMO GENERATOR] Rendering {total_frames} frames ({duration_sec}s) of simulated campus video...")
    bg_template = generate_campus_background(width, height)
    
    # Define simulated pedestrian trajectories
    # Pedestrian 1: Normal walker across bottom quad
    # Pedestrian 2: Walker moving diagonally
    # Pedestrian 3: Enters restricted zone (x: 420-620, y: 40-240) around frame 120
    # Pedestrian 4: Fast runner (rapid movement) across the center around frame 200
    # Pedestrian group 5..10: Crowd gathering in courtyard around frame 300
    
    palette = [
        (180, 120, 50),
        (50, 140, 180),
        (120, 60, 160),
        (60, 160, 80),
        (190, 80, 80),
        (200, 180, 60)
    ]
    
    for f in range(total_frames):
        frame = bg_template.copy()
        time_sec = f / fps
        
        # 1. Continuous walker 1 (Left to Right)
        p1_x = (80 + int(f * 2.2)) % (width + 100) - 50
        p1_y = int(height * 0.82)
        draw_pedestrian(frame, p1_x, p1_y, scale=1.1, color=palette[0], leg_phase=f * 0.4)
        
        # 2. Continuous walker 2 (Right to Left)
        p2_x = (width + 50 - int(f * 1.8)) % (width + 120) - 50
        p2_y = int(height * 0.68)
        draw_pedestrian(frame, p2_x, p2_y, scale=0.85, color=palette[1], leg_phase=f * 0.35)
        
        # 3. Walker 3: Restricted Area Breacher (walks into top-right zone x:480, y:180)
        p3_phase = (f % 300) / 300.0
        p3_x = int(320 + p3_phase * 220)
        p3_y = int(240 - math.sin(p3_phase * math.pi) * 80)
        draw_pedestrian(frame, p3_x, p3_y, scale=0.75, color=palette[2], leg_phase=f * 0.45)
        
        # 4. Rapid Sprinter / Runner (triggers Unusual Rapid Movement anomaly)
        # Sprinter appears between frame 150..260 and 380..490 with high velocity
        if (150 <= (f % 300) <= 220):
            s_frac = ((f % 300) - 150) / 70.0
            runner_x = int(50 + s_frac * (width - 100))
            runner_y = int(height * 0.74)
            # High frequency arm/leg swing
            draw_pedestrian(frame, runner_x, runner_y, scale=1.0, color=(40, 40, 220), leg_phase=f * 1.2)
            
        # 5. Crowd Group gathering in center (testing crowd counting & levels)
        if f > 200:
            for idx in range(6):
                cx = int(240 + (idx % 3) * 35 + math.sin(f * 0.05 + idx) * 5)
                cy = int(220 + (idx // 3) * 30 + math.cos(f * 0.04 + idx) * 4)
                draw_pedestrian(frame, cx, cy, scale=0.7, color=palette[idx % len(palette)], leg_phase=f * 0.1)

        writer.write(frame)
        
    writer.release()
    print(f"[DEMO GENERATOR SUCCESS] Demo video created at: {output_path}")
    return True


if __name__ == "__main__":
    create_demo_video()
