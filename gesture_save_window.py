from __future__ import annotations

import os
import time
import datetime as _dt
import xml.etree.ElementTree as ET

import pyglet
from pyglet.window import mouse

import recognizer

class _SaveGestureWindow(recognizer.GestureWindow):
    def __init__(self):
        super().__init__()

        self._drawing_start: float = 0.0
        self._raw_points:  list[tuple[int, int, int]] = []  # array for x,y, t ,ms
        self._last_points: list[tuple[int, int, int]] = []

        self._hint = pyglet.text.Label(
            "Q quit  |  SPACE draw  |  S save",
            font_name="Arial",
            font_size=14,
            x=20,
            y=20,
            anchor_x="left",
            anchor_y="bottom",
            color=(255, 255, 0, 255),
            batch=self.batch,
        )

    def _wipe(self):
        super()._wipe()
        self._raw_points.clear()

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            self._wipe()
            self._drawing_start = time.perf_counter()
            self._raw_points.append((x, y, 0))
            self.points.append((x, y))
            self.label.text = "Drawing..."

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if buttons & mouse.LEFT:
            now = int((time.perf_counter() - self._drawing_start) * 1000)
            last = self.points[-1]
            self.points.append((x, y))
            self._raw_points.append((x, y, now))
            self.lines.append(
                pyglet.shapes.Line(
                    last[0], last[1], x, y,
                    recognizer.LINE_W,
                    color=(60, 190, 255),
                    batch=self.batch,
                )
            )

    def on_mouse_release(self, x, y, button, modifiers):
        if button == mouse.LEFT and len(self.points) > 10:
            now = int((time.perf_counter() - self._drawing_start) * 1000)
            self._raw_points.append((x, y, now))
            self._last_points = self._raw_points.copy()

            res = self.recogniser.recognize(self.points)
            if res.score < 0.8:
                res.name = "No match"
            self.label.text = f"{res.name} (score = {res.score:.2f})"

            self.points.clear()
            self._raw_points.clear()

    def save_last_shape(self) -> None:
        if not self._last_points:
            self.label.text = "No Shape found"
            return

        import tkinter as tk
        from tkinter import filedialog, simpledialog

        root = tk.Tk()
        root.withdraw()

        name = simpledialog.askstring(
            "Gesture name", "Name For .XML file:", parent=root
        )
        if not name:
            root.destroy()
            return

        file_path = filedialog.asksaveasfilename(
            title="Save gesture",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml")],
            initialfile=f"{name}.xml",
        )
        if not file_path:
            root.destroy()
            return

        try:
            self._write_xml(file_path, name, self._last_points)
            self.label.text = f"Saved file successfully: {os.path.basename(file_path)}"
        except Exception as exc:
            self.label.text = f"Save failed: {exc}"
        finally:
            root.destroy()

    @staticmethod
    def _write_xml(path: str, name: str,
                   pts: list[tuple[int, int, int]]) -> None:
        total_ms = pts[-1][2] if pts else 0
        attrs = {
            "Name"       : name,
            "Subject"    : "1",
            "Speed"      : "unknown",
            "Number"     : "1",
            "NumPts"     : str(len(pts)),
            "Millseconds": str(total_ms),
            "AppName"    : "GestureApp",
            "AppVer"     : "1.0",
            "Date"       : _dt.datetime.now().strftime("%A, %B %d, %Y"),
            "TimeOfDay"  : _dt.datetime.now().strftime("%I:%M:%S %p").lstrip("0"),
        }
        gesture = ET.Element("Gesture", attrs)
        for x, y, t in pts:
            ET.SubElement(gesture, "Point",
                          {"X": str(int(x)), "Y": str(int(y)), "T": str(t)})

        tree = ET.ElementTree(gesture)

        tree.write(path, encoding="utf-8", xml_declaration=True)


GestureWindow = _SaveGestureWindow
