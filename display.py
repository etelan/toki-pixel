from __future__ import annotations

"""Display and sequencing code for Toki Pona cards."""

import os
import random
import tempfile
import time
from pathlib import Path
from typing import Protocol, Sequence

from PIL import Image
from pixoo import Pixoo

from settings import DEFAULT_DISPLAY_SIZE, DEFAULT_FONT_PATH, DEFAULT_PIXOO_IP
from data import DEFAULT_WORDS, TokiPonaData, TokiPonaWord
from rendering import CardFonts, CardLayout, CardRenderer, Color


class WordDisplayHandler(Protocol):
    def show_word(self, word: TokiPonaWord) -> None:
        ...


class RandomTokiPonaDisplay:
    """Choose which word to show; the handler decides how it is rendered."""

    def __init__(
        self,
        handler: WordDisplayHandler,
        *,
        words: Sequence[TokiPonaWord] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.handler = handler
        self.data = TokiPonaData(words or DEFAULT_WORDS, rng=rng)

    def random(self) -> TokiPonaWord:
        word = self.data.random()
        self.handler.show_word(word)
        return word

    def next(self, current: TokiPonaWord | str) -> TokiPonaWord:
        word = self.data.next(current)
        self.handler.show_word(word)
        return word

    def previous(self, current: TokiPonaWord | str) -> TokiPonaWord:
        word = self.data.previous(current)
        self.handler.show_word(word)
        return word

    def timed_cycle(self, delay_seconds: float) -> None:
        if delay_seconds <= 0:
            raise ValueError("timed delay must be greater than 0")

        seed = int(time.time())
        shuffled_words = list(self.data.all())
        seeded_rng = random.Random(seed)

        while True:
            seeded_rng.shuffle(shuffled_words)
            for word in shuffled_words:
                self.handler.show_word(word)
                time.sleep(delay_seconds)

    def timed_cycle_from(self, delay_seconds: float, start_name: str) -> None:
        if delay_seconds <= 0:
            raise ValueError("timed delay must be greater than 0")

        start_word = self._resolve_start_word(start_name)
        if start_word is None:
            raise ValueError(f"unknown toki pona word: {start_name}")

        start_index = self.data.index_by_name[start_word.name]
        ordered_words = self.data.all()[start_index:] + self.data.all()[:start_index]

        while True:
            for word in ordered_words:
                self.handler.show_word(word)
                time.sleep(delay_seconds)

    def show(self, name: str) -> TokiPonaWord:
        word = self.data.get(name)
        self.handler.show_word(word)
        return word

    def _resolve_start_word(self, start_name: str) -> TokiPonaWord | None:
        normalized = start_name.strip().lower()
        if not normalized:
            return None

        if normalized in self.data.words_by_name:
            return self.data.get(normalized)

        if len(normalized) == 1:
            return self.data.first_starting_with(normalized)

        return None


class PixooHandler:
    """Render a card and push it to the Pixoo."""

    def __init__(
        self,
        ip_address: str = DEFAULT_PIXOO_IP,
        *,
        size: int = DEFAULT_DISPLAY_SIZE,
        font_path: str | None = None,
        debug: bool = False,
    ) -> None:
        self.ip_address = self._require_ip_address(ip_address)
        self.size = self._require_display_size(size)
        self.font_path = self._resolve_font_path(font_path)
        self.renderer = CardRenderer(size=self.size, font_path=self.font_path)
        self.display = Pixoo(self.ip_address, self.size, debug)

    def show_word(self, word: TokiPonaWord) -> None:
        image = self.renderer.render_card(word)
        png_path = self._save_temp_image(image)
        try:
            self.display.draw_image(png_path)
            self.display.push()
        except Exception as exc:
            print(f"failed to reach Pixoo at {self.ip_address}: {exc}")
        finally:
            os.unlink(png_path)

    def _require_ip_address(self, ip_address: str | None) -> str:
        if not ip_address:
            raise ValueError("Pixoo IP address must not be empty")
        return ip_address

    def _require_display_size(self, size: int) -> int:
        if size <= 0:
            raise ValueError("display size must be greater than 0")
        return size

    def _resolve_font_path(self, font_path: str | None) -> str:
        candidate = Path(font_path) if font_path else DEFAULT_FONT_PATH
        if not candidate.is_file():
            raise FileNotFoundError(f"font file not found: {candidate}")
        return str(candidate)

    def _save_temp_image(self, image: Image.Image) -> str:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = temp_file.name

        image.save(temp_path)
        return temp_path


def send_random(
    ip: str = DEFAULT_PIXOO_IP,
    *,
    size: int = DEFAULT_DISPLAY_SIZE,
) -> TokiPonaWord:
    """Send one random Toki Pona card to the Pixoo (one-liner helper)."""
    return RandomTokiPonaDisplay(PixooHandler(ip, size=size)).random()


def send_word(
    name: str,
    ip: str = DEFAULT_PIXOO_IP,
    *,
    size: int = DEFAULT_DISPLAY_SIZE,
) -> TokiPonaWord:
    """Send a specific Toki Pona word to the Pixoo by name (one-liner helper)."""
    display = RandomTokiPonaDisplay(PixooHandler(ip, size=size))
    return display.show(name)


__all__ = [
    "CardFonts",
    "CardLayout",
    "Color",
    "DEFAULT_FONT_PATH",
    "DEFAULT_PIXOO_IP",
    "DEFAULT_WORDS",
    "PixooHandler",
    "RandomTokiPonaDisplay",
    "TokiPonaData",
    "TokiPonaWord",
    "send_random",
    "send_word",
]