from __future__ import annotations

"""Rendering logic for a single Toki Pona card image."""

import base64
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

from settings import (
    BACKGROUND,
    CARD_GLYPH_AREA_PADDING,
    CARD_MEANING_FONT_SCALE,
    CARD_MEANING_LINE_GAP,
    CARD_MIN_MEANING_FIT_SIZE,
    CARD_MIN_MEANING_FONT_SIZE,
    CARD_MIN_SYMBOL_FONT_SIZE,
    CARD_MIN_WORD_FIT_SIZE,
    CARD_MIN_WORD_FONT_SIZE,
    CARD_SYMBOL_DEFAULT_SCALE,
    CARD_SYMBOL_FONT_SCALE,
    CARD_SYMBOL_GAP,
    CARD_TEXT_BOTTOM_PADDING,
    CARD_TEXT_GAP,
    CARD_TEXT_SIDE_PADDING,
    CARD_WORD_FONT_SCALE,
    DEFAULT_FONT_PATH,
    FOREGROUND,
    GLYPH_SCALE_OVERRIDES,
    MEANING_COLOR,
    TITLE_LINE_OVERRIDES,
    WORD_COLOR,
)
from data import TokiPonaWord


Color = tuple[int, int, int]


@dataclass(frozen=True)
class CardFonts:
    symbol: ImageFont.FreeTypeFont
    word: ImageFont.FreeTypeFont
    meaning: ImageFont.FreeTypeFont


@dataclass(frozen=True)
class CardLayout:
    symbol_height: int
    symbol_y: int
    word_y: int
    meaning_y: int


class CardRenderer:
    """Turn a Toki Pona word into a small image ready for the Pixoo."""

    def __init__(self, *, size: int = 64, font_path: str | None = None) -> None:
        self.size = self._require_display_size(size)
        self.font_path = self._resolve_font_path(font_path)

    def render_card(self, word: TokiPonaWord) -> Image.Image:
        image = Image.new("RGBA", (self.size, self.size), (*BACKGROUND, 255))
        canvas = ImageDraw.Draw(image)
        glyph_image = self._load_glyph_image(word)
        word_lines, fonts, meaning_lines, layout = self._fit_card_text(canvas, glyph_image.height, word)
        glyph_image = self._fit_glyph_to_height(glyph_image, layout.symbol_height)

        self._paste_centered_image(image, glyph_image, layout.symbol_y)
        self._draw_centered_multiline_text(canvas, word_lines, layout.word_y, fonts.word, WORD_COLOR, line_gap=0)
        self._draw_centered_multiline_text(
            canvas,
            meaning_lines,
            layout.meaning_y,
            fonts.meaning,
            MEANING_COLOR,
            line_gap=CARD_MEANING_LINE_GAP,
        )
        return image.convert("RGB")

    def _require_display_size(self, size: int) -> int:
        if size <= 0:
            raise ValueError("display size must be greater than 0")
        return size

    def _resolve_font_path(self, font_path: str | None) -> str:
        candidate = Path(font_path) if font_path else DEFAULT_FONT_PATH
        if not candidate.is_file():
            raise FileNotFoundError(f"font file not found: {candidate}")
        return str(candidate)

    def _build_fonts(self, *, word_size: int | None = None, meaning_size: int | None = None) -> CardFonts:
        base_word_size = max(int(self.size * CARD_WORD_FONT_SCALE), CARD_MIN_WORD_FONT_SIZE)
        base_meaning_size = max(int(self.size * CARD_MEANING_FONT_SCALE), CARD_MIN_MEANING_FONT_SIZE)
        symbol_size = max(int(self.size * CARD_SYMBOL_FONT_SCALE), CARD_MIN_SYMBOL_FONT_SIZE)
        return CardFonts(
            symbol=self._load_font(symbol_size),
            word=self._load_font(word_size or base_word_size),
            meaning=self._load_font(meaning_size or base_meaning_size),
        )

    def _fit_card_text(
        self,
        canvas: ImageDraw.ImageDraw,
        symbol_height: int,
        word: TokiPonaWord,
    ) -> tuple[tuple[str, ...], CardFonts, tuple[str, ...], CardLayout]:
        base_fonts = self._build_fonts()
        minimum_word_size = max(int(self.size * 0.08), CARD_MIN_WORD_FIT_SIZE)
        minimum_meaning_size = max(int(self.size * 0.08), CARD_MIN_MEANING_FIT_SIZE)
        last_attempt: tuple[tuple[str, ...], CardFonts, tuple[str, ...], CardLayout] | None = None

        for word_size in range(base_fonts.word.size, minimum_word_size - 1, -1):
            for meaning_size in range(base_fonts.meaning.size, minimum_meaning_size - 1, -1):
                fonts = self._build_fonts(word_size=word_size, meaning_size=meaning_size)
                word_lines = self._word_lines(word.name)
                meaning_lines = self._wrap_text(
                    canvas,
                    word.meaning,
                    fonts.meaning,
                    max_width=self.size - CARD_TEXT_SIDE_PADDING,
                )
                layout = self._build_layout(canvas, symbol_height, fonts, word_lines, meaning_lines)
                last_attempt = (word_lines, fonts, meaning_lines, layout)

                if self._card_text_fits(canvas, layout, fonts, word_lines, meaning_lines):
                    return word_lines, fonts, meaning_lines, layout

        if last_attempt is None:
            raise ValueError("unable to fit card text")

        return last_attempt

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(self.font_path, size=size)

    def _build_layout(
        self,
        canvas: ImageDraw.ImageDraw,
        symbol_height: int,
        fonts: CardFonts,
        word_lines: Sequence[str],
        meaning_lines: Sequence[str],
    ) -> CardLayout:
        word_height = self._multiline_text_height(canvas, word_lines, fonts.word, line_gap=0)
        meaning_height = self._multiline_text_height(canvas, meaning_lines, fonts.meaning, line_gap=CARD_MEANING_LINE_GAP)
        total_text_height = word_height + CARD_TEXT_GAP + meaning_height
        available_symbol_height = max(self.size - total_text_height - CARD_SYMBOL_GAP - 1, 1)
        fitted_symbol_height = min(symbol_height, available_symbol_height)
        total_height = fitted_symbol_height + CARD_SYMBOL_GAP + total_text_height
        symbol_y = max((self.size - total_height) // 2, 0)
        word_y = symbol_y + fitted_symbol_height + CARD_SYMBOL_GAP
        meaning_y = word_y + word_height + CARD_TEXT_GAP
        return CardLayout(
            symbol_height=fitted_symbol_height,
            symbol_y=symbol_y,
            word_y=word_y,
            meaning_y=meaning_y,
        )

    def _card_text_fits(
        self,
        canvas: ImageDraw.ImageDraw,
        layout: CardLayout,
        fonts: CardFonts,
        word_lines: Sequence[str],
        meaning_lines: Sequence[str],
    ) -> bool:
        word_width = max(self._text_width(canvas, line, fonts.word) for line in word_lines)
        meaning_width = max(self._text_width(canvas, line, fonts.meaning) for line in meaning_lines)
        meaning_height = self._multiline_text_height(canvas, meaning_lines, fonts.meaning, line_gap=CARD_MEANING_LINE_GAP)
        meaning_bottom = layout.meaning_y + meaning_height
        max_text_width = self.size - CARD_TEXT_SIDE_PADDING
        return (
            word_width <= max_text_width
            and meaning_width <= max_text_width
            and meaning_bottom <= self.size - CARD_TEXT_BOTTOM_PADDING
        )

    def _word_lines(self, word_name: str) -> tuple[str, ...]:
        return TITLE_LINE_OVERRIDES.get(word_name, (word_name,))

    def _multiline_text_height(
        self,
        canvas: ImageDraw.ImageDraw,
        lines: Sequence[str],
        font: ImageFont.ImageFont,
        *,
        line_gap: int,
    ) -> int:
        if not lines:
            return 0

        line_advance = self._line_advance(font)
        last_line_bottom = self._text_bottom(canvas, lines[-1], font)
        return ((line_advance + line_gap) * (len(lines) - 1)) + last_line_bottom

    def _load_glyph_image(self, word: TokiPonaWord) -> Image.Image:
        glyph_image = Image.open(BytesIO(base64.b64decode(word.glyph_png_base64))).convert("RGBA")
        return self._prepare_glyph_image(glyph_image, word.name)

    def _prepare_glyph_image(self, glyph_image: Image.Image, word_name: str) -> Image.Image:
        alpha = glyph_image.getchannel("A")
        white_glyph = Image.new("RGBA", glyph_image.size, (*FOREGROUND, 0))
        white_glyph.putalpha(alpha)

        glyph_scale = GLYPH_SCALE_OVERRIDES.get(word_name, CARD_SYMBOL_DEFAULT_SCALE)
        symbol_area_limit = max((self.size // 2) - CARD_GLYPH_AREA_PADDING, 1)
        max_width = min(max(int(self.size * glyph_scale), 1), symbol_area_limit)
        max_height = min(max(int(self.size * glyph_scale), 1), symbol_area_limit)
        white_glyph.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        return white_glyph

    def _paste_centered_image(self, image: Image.Image, glyph_image: Image.Image, y: int) -> None:
        x = max((self.size - glyph_image.width) // 2, 0)
        image.alpha_composite(glyph_image, (x, y))

    def _fit_glyph_to_height(self, glyph_image: Image.Image, max_height: int) -> Image.Image:
        if glyph_image.height <= max_height:
            return glyph_image

        resized = glyph_image.copy()
        max_width = max(int((glyph_image.width / glyph_image.height) * max_height), 1)
        resized.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        return resized

    def _draw_centered_multiline_text(
        self,
        canvas: ImageDraw.ImageDraw,
        lines: Sequence[str],
        start_y: int,
        font: ImageFont.ImageFont,
        color: Color,
        *,
        line_gap: int,
    ) -> None:
        y = start_y
        line_advance = self._line_advance(font)

        for line in lines:
            width = self._text_width(canvas, line, font)
            x = max((self.size - width) // 2, 0)
            canvas.text((x, y), line, font=font, fill=color)
            y += line_advance + line_gap

    def _wrap_text(
        self,
        canvas: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
        *,
        max_width: int,
    ) -> tuple[str, ...]:
        words = text.split()
        if not words:
            return ("",)

        lines: list[str] = []
        current_line = words[0]

        for word in words[1:]:
            candidate = f"{current_line} {word}"
            if self._text_width(canvas, candidate, font) <= max_width:
                current_line = candidate
                continue

            lines.append(current_line)
            current_line = word

        lines.append(current_line)
        return tuple(lines)

    def _text_width(self, canvas: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
        left, _, right, _ = canvas.textbbox((0, 0), text, font=font)
        return right - left

    def _text_bottom(self, canvas: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
        _, top, _, bottom = canvas.textbbox((0, 0), text, font=font)
        return bottom - top

    def _line_advance(self, font: ImageFont.ImageFont) -> int:
        left, top, right, bottom = font.getbbox("Ag")
        return max(bottom - top, right - left, 1)


__all__ = ["CardFonts", "CardLayout", "CardRenderer", "Color"]