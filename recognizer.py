#BASIERT AUF https://depts.washington.edu/acelab/proj/dollar/dollar.js
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import pyglet
from pyglet.window import mouse

NUM_POINTS      = 64
SQUARE_SIZE     = 250.0
ORIGIN          = (0.0, 0.0)
DIAGONAL        = math.hypot(SQUARE_SIZE, SQUARE_SIZE)
HALF_DIAGONAL   = 0.5 * DIAGONAL
ANGLE_RANGE     = math.radians(45.0)
ANGLE_PRECISION = math.radians(2.0)
PHI             = 0.5 * (-1.0 + math.sqrt(5.0))

def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _path_length(pts: List[Tuple[float, float]]) -> float:
    return sum(_dist(pts[i - 1], pts[i]) for i in range(1, len(pts)))

#converted to python from javascript from https://depts.washington.edu/acelab/proj/dollar/dollar.js
def resample(points: List[Tuple[float, float]],
             n: int = NUM_POINTS) -> List[Tuple[float, float]]:
    if not points:
        return []
    total_length = _path_length(points)

    if total_length == 0:
        return [points[0] for _ in range(n)]
    I = total_length / (n - 1)
    D = 0.0
    new_pts = [points[0]]
    pts = list(points)
    i = 1
    while i < len(pts) and len(new_pts) < n:
        d = _dist(pts[i - 1], pts[i])
        if (D + d) >= I:
            t  = (I - D) / d
            qx = pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0])
            qy = pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])
            q  = (qx, qy)
            new_pts.append(q)
            pts.insert(i, q)
            D = 0.0
            i += 1
        else:
            D += d
            i += 1

    while len(new_pts) < n:
        new_pts.append(pts[-1])
    return new_pts

def centroid(pts: List[Tuple[float, float]]) -> Tuple[float, float]:
    x = sum(p[0] for p in pts) / len(pts)
    y = sum(p[1] for p in pts) / len(pts)
    return x, y


def indicative_angle(pts: List[Tuple[float, float]]) -> float:
    c = centroid(pts)
    return math.atan2(c[1] - pts[0][1], c[0] - pts[0][0])


def rotate_by(pts: List[Tuple[float, float]], rad: float
             ) -> List[Tuple[float, float]]:
    c = centroid(pts)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    def _rot(p):
        dx, dy = p[0] - c[0], p[1] - c[1]
        return (dx * cos_r - dy * sin_r + c[0],
                dx * sin_r + dy * cos_r + c[1])
    return [_rot(p) for p in pts]

def _bounding_box(pts: List[Tuple[float, float]]
                 ) -> Tuple[float, float, float, float]:
    xs, ys = zip(*pts)
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def scale_to(pts: List[Tuple[float, float]],
             size: float = SQUARE_SIZE) -> List[Tuple[float, float]]:
    _, _, w, h = _bounding_box(pts)
    w = w or 1.0
    h = h or 1.0
    return [(p[0] * (size / w), p[1] * (size / h)) for p in pts]


def translate_to(pts: List[Tuple[float, float]],
                 target: Tuple[float, float] = ORIGIN
                ) -> List[Tuple[float, float]]:
    c = centroid(pts)
    return [(p[0] + target[0] - c[0], p[1] + target[1] - c[1]) for p in pts]

def _path_distance(a: List[Tuple[float, float]],
                   b: List[Tuple[float, float]]) -> float:
    return sum(_dist(p, q) for p, q in zip(a, b)) / len(a)


def _distance_at_angle(pts: List[Tuple[float, float]],
                       tmpl_pts: List[Tuple[float, float]],
                       rad: float) -> float:
    return _path_distance(rotate_by(pts, rad), tmpl_pts)


def distance_at_best_angle(pts: List[Tuple[float, float]],
                           tmpl_pts: List[Tuple[float, float]],
                           a: float, b: float,
                           thresh: float) -> float:
    x1 = PHI * a + (1 - PHI) * b
    f1 = _distance_at_angle(pts, tmpl_pts, x1)
    x2 = (1 - PHI) * a + PHI * b
    f2 = _distance_at_angle(pts, tmpl_pts, x2)
    while abs(b - a) > thresh:
        if f1 < f2:
            b, x2, f2 = x2, x1, f1
            x1 = PHI * a + (1 - PHI) * b
            f1 = _distance_at_angle(pts, tmpl_pts, x1)
        else:
            a, x1, f1 = x1, x2, f2
            x2 = (1 - PHI) * a + PHI * b
            f2 = _distance_at_angle(pts, tmpl_pts, x2)
    return min(f1, f2)

@dataclass
class Template:
    name      : str
    raw_points: List[Tuple[float, float]]
    points    : List[Tuple[float, float]] = None

    def __post_init__(self):
        pts = resample(self.raw_points)
        pts = rotate_by(pts, -indicative_angle(pts))
        pts = scale_to(pts)
        pts = translate_to(pts)
        self.points = pts


@dataclass
class Result:
    name : str
    score: float

class DollarRecognizer:
    def __init__(self, window_h: int):
        self.templates: List[Template] = []
        self._win_h = window_h

    def add_template(self, name: str, pts: List[Tuple[float, float]]):
        self.templates.append(Template(name, pts))

    def recognize(self, points: List[Tuple[float, float]]) -> Result:
        #reverse y for pyglet window since it measures from bottom
        points = [(x, self._win_h - y) for (x, y) in points]

        candidate = Template("", points)

        best_dist = float("inf")
        best_name = "No match"
        for tmpl in self.templates:
            d = distance_at_best_angle(candidate.points, tmpl.points,
                                       -ANGLE_RANGE, ANGLE_RANGE,
                                       ANGLE_PRECISION)
            if d < best_dist:
                best_dist = d
                best_name = tmpl.name

        score = 1.0 - best_dist / HALF_DIAGONAL
        return Result(best_name, score)

gesture_points = {
    "rectangle": [
        (78,149),(78,153),(78,157),(78,160),(79,162),(79,164),(79,167),(79,169),(79,173),(79,178),
        (79,183),(80,189),(80,193),(80,198),(80,202),(81,208),(81,210),(81,216),(82,222),(82,224),
        (82,227),(83,229),(83,231),(85,230),(88,232),(90,233),(92,232),(94,233),(99,232),(102,233),
        (106,233),(109,234),(117,235),(123,236),(126,236),(135,237),(142,238),(145,238),(152,238),
        (154,239),(165,238),(174,237),(179,236),(186,235),(191,235),(195,233),(197,233),(200,233),
        (201,235),(201,233),(199,231),(198,226),(198,220),(196,207),(195,195),(195,181),(195,173),
        (195,163),(194,155),(192,145),(192,143),(192,138),(191,135),(191,133),(191,130),(190,128),
        (188,129),(186,129),(181,132),(173,131),(162,131),(151,132),(149,132),(138,132),(136,132),
        (122,131),(120,131),(109,130),(107,130),(90,132),(81,133),(76,133)
    ],
    "circle": [
        (127,141),(124,140),(120,139),(118,139),(116,139),(111,140),(109,141),(104,144),(100,147),
        (96,152),(93,157),(90,163),(87,169),(85,175),(83,181),(82,190),(82,195),(83,200),(84,205),
        (88,213),(91,216),(96,219),(103,222),(108,224),(111,224),(120,224),(133,223),(142,222),
        (152,218),(160,214),(167,210),(173,204),(178,198),(179,196),(182,188),(182,177),(178,167),
        (170,150),(163,138),(152,130),(143,129),(140,131),(129,136),(126,139)
    ],
    "check": [
        (91,185),(93,185),(95,185),(97,185),(100,188),(102,189),(104,190),(106,193),(108,195),
        (110,198),(112,201),(114,204),(115,207),(117,210),(118,212),(120,214),(121,217),(122,219),
        (123,222),(124,224),(126,226),(127,229),(129,231),(130,233),(129,231),(129,228),(129,226),
        (129,224),(129,221),(129,218),(129,212),(129,208),(130,198),(132,189),(134,182),(137,173),
        (143,164),(147,157),(151,151),(155,144),(161,137),(165,131),(171,122),(174,118),(176,114),
        (177,112),(177,114),(175,116),(173,118)
    ],
    "delete": [
        (123,129),(123,131),(124,133),(125,136),(127,140),(129,142),(133,148),(137,154),(143,158),
        (145,161),(148,164),(153,170),(158,176),(160,178),(164,183),(168,188),(171,191),(175,196),
        (178,200),(180,202),(181,205),(184,208),(186,210),(187,213),(188,215),(186,212),(183,211),
        (177,208),(169,206),(162,205),(154,207),(145,209),(137,210),(129,214),(122,217),(118,218),
        (111,221),(109,222),(110,219),(112,217),(118,209),(120,207),(128,196),(135,187),(138,183),
        (148,167),(157,153),(163,145),(165,142),(172,133),(177,127),(179,127),(180,125)
    ],
    "pigtail": [
        (81,219),(84,218),(86,220),(88,220),(90,220),(92,219),(95,220),(97,219),(99,220),(102,218),
        (105,217),(107,216),(110,216),(113,214),(116,212),(118,210),(121,208),(124,205),(126,202),
        (129,199),(132,196),(136,191),(139,187),(142,182),(144,179),(146,174),(148,170),(149,168),
        (151,162),(152,160),(152,157),(152,155),(152,151),(152,149),(152,146),(149,142),(148,139),
        (145,137),(141,135),(139,135),(134,136),(130,140),(128,142),(126,145),(122,150),(119,158),
        (117,163),(115,170),(114,175),(117,184),(120,190),(125,199),(129,203),(133,208),(138,213),
        (145,215),(155,218),(164,219),(166,219),(177,219),(182,218),(192,216),(196,213),(199,212),
        (201,211)
    ],
}

WINDOW_W, WINDOW_H = 1600, 900
LINE_W= 5


class GestureWindow(pyglet.window.Window):
    def __init__(self):
        super().__init__(WINDOW_W, WINDOW_H, "$1 Gesture Recognizer", resizable=False)
        pyglet.gl.glLineWidth(LINE_W)

        self.recogniser = DollarRecognizer(window_h=self.height)
        for name, pts in gesture_points.items():
            self.recogniser.add_template(name, pts)

        self.points: List[Tuple[float, float]] = []
        self.lines : List[pyglet.shapes.Line]  = []
        self.batch  = pyglet.graphics.Batch()
        self.label  = pyglet.text.Label(
            "Draw a Gesture (Rectangle, Circle, Check, Delete, Pigtail)",
            x=10, y=self.height - 34, batch=self.batch, font_size=23
        )

    def _wipe(self):
        for l in self.lines:
            l.delete()
        self.lines.clear()
        self.points.clear()

    def on_mouse_press(self, x, y, button, modifiers):
        if button == mouse.LEFT:
            self._wipe()
            self.points.append((x, y))
            self.label.text = "Drawing..."

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if buttons & mouse.LEFT:
            last = self.points[-1]
            self.points.append((x, y))
            self.lines.append(
                pyglet.shapes.Line(last[0], last[1], x, y, LINE_W,
                                   color=(60, 190, 255), batch=self.batch)
            )

    def on_mouse_release(self, x, y, button, modifiers):
        if button == mouse.LEFT and len(self.points) > 10:
            res = self.recogniser.recognize(self.points)
            if(res.score < 0.8):
                res.name = "No match"
            self.label.text = f"{res.name} (score = {res.score:.2f})"
            self.points.clear()

    def on_draw(self):
        self.clear()
        self.batch.draw()



if __name__ == "__main__":
    GestureWindow()
    pyglet.app.run()