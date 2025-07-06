import RPi.GPIO as GPIO
import cv2
import mediapipe as mp
import csv
from datetime import datetime
import os

LED_PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT, initial=GPIO.LOW)

# INITIALISATION CSV
csv_file = "DATA_BASE.csv"
if not os.path.isfile(csv_file):
    with open(csv_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Horodatage", "Main", "Geste", "hands_in_zone"])

# Initialisation de MediaPipe Hands
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False,
                       max_num_hands=10,
                       min_detection_confidence=0.7,
                       min_tracking_confidence=0.7)

# Détection du geste 
def detect_gesture(landmarks, hand_label):
    finger_tips = [8, 12, 16, 20]
    finger_bases = [6, 10, 14, 18]
    open_fingers = 0

    for tip, base in zip(finger_tips, finger_bases):
        if hand_label == "Right":
            if landmarks[tip].y < landmarks[base].y:
                open_fingers += 1
        else:
            if landmarks[tip].y > landmarks[base].y:
                open_fingers += 1

    return "Main ouverte" if open_fingers >= 3 else "Poing ferme"

def video_loop():
    cap = cv2.VideoCapture(0)
    while True:
        success, frame = cap.read()
        if not success:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        h, w, _ = frame.shape

        zone_w, zone_h = 300, 300
        zone_x = (w - zone_w) // 2
        zone_y = (h - zone_h) // 2

        cv2.rectangle(frame, (zone_x, zone_y), (zone_x + zone_w, zone_y + zone_h), (0, 0, 255), 2)

        danger_detected_global = False
        danger_detected = False
        hands_in_zone = 0
        gestures = []
        hands_count = 0

        if results.multi_hand_landmarks:
            hands_count = len(results.multi_hand_landmarks)
            for idx, handLms in enumerate(results.multi_hand_landmarks):
                mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)

                hand_label = results.multi_handedness[idx].classification[0].label

                landmarks = handLms.landmark
                gesture = detect_gesture(landmarks, hand_label)
                gestures.append(gesture)

                for lm in landmarks:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    if zone_x < cx < zone_x + zone_w and zone_y < cy < zone_y + zone_h:
                        danger_detected = True
                        danger_detected_global = True
                        hands_in_zone += 1
                        break

                wrist = landmarks[0]
                wrist_x, wrist_y = int(wrist.x * w), int(wrist.y * h)
                couleur_texte = (0, 0, 255) if danger_detected else (255, 255, 0)
                cv2.putText(frame, f"Main {idx+1}: {gesture}", (wrist_x - 30, wrist_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, couleur_texte, 2)

        if danger_detected:
            GPIO.output(LED_PIN, GPIO.HIGH)
            cv2.putText(frame, "DANGER: Main dans zone interdite", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), hand_label, gesture, hands_in_zone])
        else:
            GPIO.output(LED_PIN, GPIO.LOW)

        cv2.putText(frame, f"Mains detectees: {hands_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Systeme securite", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    video_loop()
