# application for task 3
from __future__ import annotations

import math
import random
from pathlib import Path
from typing import List, Tuple, Optional

import pyglet
from pyglet.window import key, mouse
from pyglet import shapes

from pynput.mouse import Button

from pointing_input import HandMover, HandState
_hand_state = HandState()
_hand_mover = HandMover(_hand_state)
_hand_mover.start()

import recognizer as rz
_recognizer = rz.DollarRecognizer(window_h=1280)
for name, points in rz.gesture_points.items():
    _recognizer.add_template(name, points)


def recognize_shape(points: List[Tuple[float, float]], *, thr: float = 0.7
                    ) -> Optional[str]:
    result = _recognizer.recognize(points)
    return result.name if result.score >= thr else None


ASSET_DIR = Path(__file__).with_suffix("").parent / "assets"
WINDOW_W, WINDOW_H = 1280, 1280
FPS = 60
EARTH_RADIUS_PX = 64
SPAWN_EVERY = 3.0
HIT_DISTANCE = 300
SHAPES = ["rectangle", "circle", "delete", "pigtail", "check"]

pyglet.resource.path = [str(ASSET_DIR)]
pyglet.resource.reindex()

COMET_IMG          = pyglet.resource.image("comet.png")
EARTH_IMG          = pyglet.resource.image("earth.png")
EARTH_EXPLODED_IMG = pyglet.resource.image("earth_exploded.png")
EXPLOSION_FRAMES   = [pyglet.resource.image(f"comet_explosion{i}.png") for i in range(3)]

BACKGROUND_MUSIC_SRC = pyglet.resource.media("background_track.mp3", streaming=True)
EXPLOSION_SOUND_SRC  = pyglet.resource.media("explosion.wav", streaming=False)

BACKGROUND_MUSIC_PLAYER = pyglet.media.Player()
BACKGROUND_MUSIC_PLAYER.queue(BACKGROUND_MUSIC_SRC)
BACKGROUND_MUSIC_PLAYER.loop = True
BACKGROUND_MUSIC_PLAYER.play()


class Comet:
    def __init__(self, batch: pyglet.graphics.Batch, shape: str):
        self.shape  = shape
        self.batch  = batch
        self.sprite = pyglet.sprite.Sprite(COMET_IMG, batch=batch)

        side = random.choice(("left", "right", "top", "bottom"))
        if side == "left":
            self.x, self.y = -self.sprite.width, random.uniform(0, WINDOW_H)
        elif side == "right":
            self.x, self.y = WINDOW_W + self.sprite.width, random.uniform(0, WINDOW_H)
        elif side == "top":
            self.x, self.y = random.uniform(0, WINDOW_W), WINDOW_H + self.sprite.height
        else:
            self.x, self.y = random.uniform(0, WINDOW_W), -self.sprite.height

        dx, dy = WINDOW_W / 2 - self.x, WINDOW_H / 2 - self.y
        length = math.hypot(dx, dy)
        self.vx, self.vy = dx / length, dy / length
        self.speed = random.uniform(40, 90)

        self.sprite.update(x=self.x, y=self.y)

        self.label = pyglet.text.Label(
            shape,
            font_name="Arial",
            font_size=22,
            anchor_x="center",
            anchor_y="center",
            x=self.x + self.sprite.width * 0.5,
            y=self.y + self.sprite.height * 0.5,
            color=(255, 230, 130, 255),
            batch=batch,
        )

        self.explosion_frames = [pyglet.sprite.Sprite(img, batch=batch)
                                 for img in EXPLOSION_FRAMES]
        for sprite in self.explosion_frames:
            sprite.visible = False
        self.is_exploding = False
        self._elapsed_explosion_time = 0.0

    def update(self, delta_time: float) -> bool:
        if self.is_exploding:
            self._elapsed_explosion_time += delta_time
            frame_index = int(self._elapsed_explosion_time / 0.10)
            if frame_index >= len(self.explosion_frames):
                for sprite in self.explosion_frames:
                    sprite.delete()
                self.sprite.delete()
                self.label.delete()
                return False

            for idx, sprite in enumerate(self.explosion_frames):
                sprite.visible = idx == frame_index
            return True

        self.x += self.vx * self.speed * delta_time
        self.y += self.vy * self.speed * delta_time
        self.sprite.update(x=self.x, y=self.y)
        self.label.x = self.x + self.sprite.width * 0.5
        self.label.y = self.y + self.sprite.height * 0.5
        return True

    def distance_to_earth(self) -> float:
        return math.hypot(self.x - WINDOW_W / 2, self.y - WINDOW_H / 2)

    def blast(self):
        self.is_exploding = True
        self.sprite.visible = False
        self.label.visible = False

        for sprite in self.explosion_frames:
            sprite.x, sprite.y = self.x, self.y

        EXPLOSION_SOUND_SRC.play()


class GameWindow(pyglet.window.Window):
    def __init__(self):
        super().__init__(WINDOW_W, WINDOW_H, "Shape Defender", resizable=False)
        globals()["_recognizer"]._win_h = self.height

        self.background_img = pyglet.resource.image("spacebackground.png")
        self.background_sprite = pyglet.sprite.Sprite(self.background_img)
        self.background_sprite.scale = max(
            WINDOW_W / self.background_sprite.width,
            WINDOW_H / self.background_sprite.height,
        )

        self.batch = pyglet.graphics.Batch()

        self.earth_sprite = pyglet.sprite.Sprite(
            EARTH_IMG,
            x=WINDOW_W / 2 - 32,
            y=WINDOW_H / 2,
            batch=self.batch,
        )
        self._reset_earth_sprite()

        self.comets: List[Comet] = []
        self.score = 0
        self.game_over = False

        self.score_label = pyglet.text.Label(
            "Score: 0",
            x=10,
            y=WINDOW_H - 30,
            font_size=18,
            batch=self.batch,
        )
        self.game_over_label: Optional[pyglet.text.Label] = None

        self.draw_points: List[Tuple[float, float]] = []
        self.is_drawing = False

        pyglet.clock.schedule_interval(self._spawn_comet, SPAWN_EVERY)
        pyglet.clock.schedule_interval(self._update_world, 1 / FPS)

    def _reset_earth_sprite(self) -> None:
        self.earth_sprite.image = EARTH_IMG
        self.earth_sprite.anchor_x = self.earth_sprite.image.width / 2
        self.earth_sprite.anchor_y = self.earth_sprite.image.height / 2
        self.earth_sprite.scale = EARTH_RADIUS_PX / (self.earth_sprite.image.width / 2)

    def _spawn_comet(self, _dt: float) -> None:
        if not self.game_over:
            self.comets.append(Comet(self.batch, random.choice(SHAPES)))

    def _update_world(self, delta_time: float) -> None:
        if self.game_over:
            return

        for comet in self.comets[:]:
            if not comet.update(delta_time):
                self.comets.remove(comet)
                continue
            if not comet.is_exploding and comet.distance_to_earth() < EARTH_RADIUS_PX:
                self._trigger_game_over()

        self.score_label.text = f"Score: {self.score}"

    def _trigger_game_over(self) -> None:
        self.game_over = True
        pyglet.clock.unschedule(self._spawn_comet)

        self.earth_sprite.image = EARTH_EXPLODED_IMG
        self.earth_sprite.anchor_x = self.earth_sprite.image.width / 2
        self.earth_sprite.anchor_y = self.earth_sprite.image.height / 2
        self.earth_sprite.scale = EARTH_RADIUS_PX / (self.earth_sprite.image.width / 2)
        EXPLOSION_SOUND_SRC.play()

        self.game_over_label = pyglet.text.Label(
            f"Game over! Score = {self.score} | Press R to restart!",
            x=WINDOW_W / 2,
            y=WINDOW_H / 2,
            anchor_x="center",
            anchor_y="center",
            font_size=32,
            batch=self.batch,
        )

    def _restart_game(self) -> None:
        for comet in self.comets:
            comet.sprite.delete()
            comet.label.delete()
            for sprite in comet.explosion_frames:
                sprite.delete()
        self.comets.clear()

        if self.game_over_label is not None:
            self.game_over_label.delete()
            self.game_over_label = None

        self._reset_earth_sprite()
        self.score = 0
        self.score_label.text = "Score: 0"

        self.game_over = False
        pyglet.clock.schedule_interval(self._spawn_comet, SPAWN_EVERY)

    def on_mouse_press(self, x: float, y: float, button: int, _mods):
        if button == mouse.LEFT and not self.game_over:
            self.is_drawing = True
            self.draw_points = [(x, y)]

    def on_mouse_drag(self, x: float, y: float, _dx, _dy, buttons, _mods):
        if self.is_drawing and buttons & mouse.LEFT:
            self.draw_points.append((x, y))

    def on_mouse_release(self, x: float, y: float, button: int, _mods):
        if button != mouse.LEFT or not self.is_drawing:
            return
        self.is_drawing = False

        if len(self.draw_points) < 10:
            self.draw_points.clear()
            return

        shape_name = recognize_shape(self.draw_points)
        if shape_name is None:
            self.draw_points.clear()
            return

        closest: Optional[Tuple[Comet, float]] = None
        for comet in self.comets:
            if comet.shape != shape_name or comet.is_exploding:
                continue
            distance = math.hypot(comet.x - x, comet.y - y)
            if distance < HIT_DISTANCE and (closest is None or distance < closest[1]):
                closest = (comet, distance)

        if closest:
            closest[0].blast()
            self.score += 1

        self.draw_points.clear()

    @staticmethod
    def _draw_polyline(points: List[Tuple[float, float]]):
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            shapes.Line(
                x1,
                y1,
                x2,
                y2,
                thickness=3,
                color=(255, 255, 255),
                batch=None,
            ).draw()

    def on_draw(self):
        self.clear()
        self.background_sprite.draw()
        self.batch.draw()
        if self.is_drawing and len(self.draw_points) > 1:
            self._draw_polyline(self.draw_points)

    def on_key_press(self, symbol: int, _mods):
        if symbol == key.ESCAPE:
            self.close()
        elif symbol == key.R and self.game_over:
            self._restart_game()
        elif symbol == key.SPACE: #key.D
            if _hand_mover is not None:
                _hand_mover._mouse.press(Button.left)

    def on_key_release(self, symbol: int, _mods):
        if symbol == key.SPACE and _hand_mover is not None:
            _hand_mover._mouse.release(Button.left)

if __name__ == "__main__":
    try:
        GameWindow()
        pyglet.app.run()
    finally:
        if _hand_mover is not None:
            _hand_mover.running = False
            _hand_mover.join(timeout=2.0)
