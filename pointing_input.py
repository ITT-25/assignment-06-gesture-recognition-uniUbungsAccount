from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import mediapipe as mp
import pyglet
from pyglet.window import key
from pynput.mouse import Controller as MouseController, Button

from gesture_save_window import GestureWindow

SMOOTHING         = 0.33
PREVIEW_TITLE     = "Camera Feed"
INSTRUCTION_TEXT  = "Q quit  | SPACE draw (WINDOW MUST HAVE FOCUS!) | S save"

def get_screen_size() -> Tuple[int, int]:
        import tkinter as tk
        root = tk.Tk(); root.withdraw(); root.update_idletasks()
        size = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return size

@dataclass
class HandState:
    tip: Optional[Tuple[float, float]] = None

class HandMover(threading.Thread):
    def __init__(self, state: HandState,
                 cam_width: int = 1280, cam_height: int = 960):
        super().__init__(daemon=True)
        self.state = state
        self.running = True

        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self._cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            raise RuntimeError("No webcam found")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cam_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_height)
        self._cam_width, self._cam_height = cam_width, cam_height

        self._scr_w, self._scr_h = get_screen_size()
        self._mouse = MouseController()
        self._cx, self._cy = self._scr_w / 2, self._scr_h / 2

    def run(self):
        try:
            while self.running:
                ok, frame = self._cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res   = self._hands.process(rgb)

                if res.multi_hand_landmarks:
                    lms = res.multi_hand_landmarks[0].landmark
                    idx = lms[self._mp_hands.HandLandmark.INDEX_FINGER_TIP]

                    tx, ty = idx.x * self._scr_w, idx.y * self._scr_h
                    self._cx += (tx - self._cx) * SMOOTHING
                    self._cy += (ty - self._cy) * SMOOTHING
                    try:
                        self._mouse.position = (int(self._cx), int(self._cy))
                    except Exception:
                        pass

                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, res.multi_hand_landmarks[0],
                        self._mp_hands.HAND_CONNECTIONS,
                    )

                cv2.imshow(PREVIEW_TITLE,
                           cv2.resize(frame, (self._cam_width, self._cam_height)))
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
        finally:
            self._cap.release()
            cv2.destroyAllWindows()

def main():
    state = HandState()
    try:
        mover = HandMover(state)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    mover.start()

    window = GestureWindow()

    @window.event
    def on_key_press(symbol, modifiers):
        if symbol == key.SPACE:
            mover._mouse.press(Button.left)
        elif symbol == key.S:
            window.save_last_shape()
        elif symbol == key.Q:
            pyglet.app.exit()

    @window.event
    def on_key_release(symbol, modifiers):
        if symbol == key.SPACE:
            mover._mouse.release(Button.left)

    try:
        pyglet.app.run()
    finally:
        mover.running = False
        mover.join(timeout=2.0)

if __name__ == "__main__":
    main()
