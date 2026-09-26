#!/usr/bin/env python3
"""Crop and typeset a locally sourced photograph; no network or generation.

Usage: python3 render_cover.py --config cover.json --output-dir outputs/covers
Requires Pillow. Coordinates and font sizes in layout use a 2350 x 1000 design
canvas and scale to `size`. See --help for a compact configuration example.
"""

import argparse
import json
import math
from pathlib import Path
import sys

from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFont, ImageOps


LAYOUT = {
    "kicker_xy": [118, 112],
    "title_xy": [108, 262],
    "title_line_gap": 158,
    "subtitle_xy": [118, 620],
    "kicker_font_size": 42,
    "title_font_size": 118,
    "subtitle_font_size": 38,
    "kicker_min_font_size": 28,
    "title_min_font_size": 80,
    "subtitle_min_font_size": 26,
    "text_width": 1250,
    "accent_line": [118, 183, 191, 183],
    "accent_width": 4,
}
COLORS = {
    "kicker": "#FFF9EB", "title": "#FFF9EB", "subtitle": "#EEE3D0",
    "accent": "#D1AB75", "overlay": "#0A1319",
}


def number(value, label, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label} must be at most {maximum}")
    return value


def vector(value, count, label):
    if not isinstance(value, (list, tuple)) or len(value) != count:
        raise ValueError(f"{label} must contain {count} numbers")
    return [number(v, f"{label}[{i}]") for i, v in enumerate(value)]


def local_path(value, config_dir, label):
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty local path")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else config_dir / path).resolve()


def font_sources(config, config_dir):
    """Return (path, TTC index) for title and body, using known CJK fonts."""
    if "font_path" in config:
        path = local_path(config["font_path"], config_dir, "font_path")
        if not path.is_file():
            raise ValueError(f"Font does not exist: {path}")
        result = {"title": (path, 0), "body": (path, 0)}
    else:
        mac_font = Path("/System/Library/Fonts/Hiragino Sans GB.ttc")
        if mac_font.is_file():
            result = {"title": (mac_font, 2), "body": (mac_font, 0)}
        else:
            roots = [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
                     Path.home() / ".local/share/fonts", Path.home() / ".fonts",
                     Path("/Library/Fonts"), Path.home() / "Library/Fonts"]
            fonts = []
            for root in roots:
                if root.is_dir():
                    for pattern in ("*Noto*Sans*CJK*", "*Noto*Sans*SC*", "*SourceHanSans*"):
                        fonts.extend(p for p in root.rglob(pattern)
                                     if p.suffix.lower() in (".ttc", ".otf", ".ttf"))
            fonts = sorted(set(fonts), key=str)
            if not fonts:
                raise ValueError("No Chinese font found. Install Noto Sans CJK / Source Han Sans, "
                                 "or set font_path and optional font_index in the JSON config.")
            regular = next((p for p in fonts if "regular" in p.name.lower()), fonts[0])
            bold = next((p for p in fonts if "bold" in p.name.lower()), regular)
            def index(path):
                return 2 if path.suffix.lower() == ".ttc" and "NotoSansCJK" in path.name else 0
            result = {"title": (bold, index(bold)), "body": (regular, index(regular))}
    indices = config.get("font_index", {})
    if isinstance(indices, int) and not isinstance(indices, bool):
        indices = {"title": indices, "body": indices}
    if not isinstance(indices, dict) or set(indices) - {"title", "body"}:
        raise ValueError("font_index must be an integer or an object with title/body indices")
    for role, idx in indices.items():
        if isinstance(idx, bool) or not isinstance(idx, int) or idx < 0:
            raise ValueError(f"font_index.{role} must be a non-negative integer")
        result[role] = (result[role][0], idx)
    return result


def load_font(source, size):
    try:
        return ImageFont.truetype(str(source[0]), size, index=source[1])
    except OSError as error:
        raise ValueError(f"Cannot load font {source[0]} at index {source[1]}: {error}") from error


def check_chinese_glyphs(source, texts):
    font = load_font(source, 30)
    missing = font.getmask("\u0378")  # Permanently unassigned code point -> .notdef glyph.
    signature = (missing.size, bytes(missing))
    for char in sorted(set("".join(texts))):
        if "\u3400" <= char <= "\u9fff" or 0x20000 <= ord(char) <= 0x3134F:
            mask = font.getmask(char)
            if (mask.size, bytes(mask)) == signature:
                raise ValueError(f"Font {source[0]} (index {source[1]}) lacks Chinese glyph {char!r}. "
                                 "Choose a Chinese font using font_path/font_index.")


def text_value(config, field):
    value = config.get(field, "")
    if not isinstance(value, str) or "\n" in value or "\r" in value:
        raise ValueError(f"{field} must be a single-line string")
    return value.strip()


def prepare_photo(config, config_dir, size):
    photo = local_path(config.get("photo"), config_dir, "photo")
    with Image.open(photo) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    if "crop_box" in config:
        box = vector(config["crop_box"], 4, "crop_box")
        left, top, right, bottom = box
        if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
            raise ValueError(f"crop_box must be inside the EXIF-oriented source ({image.width}x{image.height})")
        box = tuple(round(v) for v in box)
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError("crop_box must have at least one pixel of width and height")
        image = image.crop(box)
        focus = (0.5, 0.5)
    else:
        focus = vector(config.get("focus", [0.5, 0.5]), 2, "focus")
        if any(v < 0 or v > 1 for v in focus):
            raise ValueError("focus coordinates must be in [0, 1]")
    image = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=tuple(focus))
    brightness = number(config.get("brightness", 1.0), "brightness", 0.01)
    return photo, ImageEnhance.Brightness(image).enhance(brightness)


def shade_left(image, opacity, color):
    width, height = image.size
    alpha = Image.new("L", (width, 1))
    alpha.putdata([round(255 * opacity * max(0, 1 - x / (width * 0.66)) ** 1.3)
                   for x in range(width)])
    shade = Image.new("RGBA", image.size, color)
    shade.putalpha(alpha.resize((width, height)))
    return Image.alpha_composite(image.convert("RGBA"), shade).convert("RGB")


def typeset(image, config, config_dir, layout, colors):
    kicker = text_value(config, "kicker")
    subtitle = text_value(config, "subtitle")
    title = config.get("title", [])
    if (not isinstance(title, list) or len(title) > 2 or
            any(not isinstance(t, str) or not t.strip() or "\n" in t or "\r" in t for t in title)):
        raise ValueError("title must be an array of one or two non-empty single-line strings (or omitted)")
    title = [t.strip() for t in title]
    opacity = number(config.get("overlay_opacity", 0.30), "overlay_opacity", 0, 0.6)
    if not (kicker or title or subtitle):
        return image.copy(), {}
    image = shade_left(image, opacity, colors["overlay"])
    draw = ImageDraw.Draw(image)
    sx, sy = image.width / 2350, image.height / 1000
    font_scale = min(sx, sy)
    max_width = number(layout["text_width"], "layout.text_width", 1) * sx
    sources = font_sources(config, config_dir)
    check_chinese_glyphs(sources["title"], title)
    check_chinese_glyphs(sources["body"], [kicker, subtitle])
    report, occupied = {}, []

    def block(kind, lines, positions, role):
        desired = number(layout[f"{kind}_font_size"], f"layout.{kind}_font_size", 1)
        minimum = number(layout[f"{kind}_min_font_size"], f"layout.{kind}_min_font_size", 1)
        start = max(1, round(desired * font_scale))
        end = max(1, round(min(desired, minimum) * font_scale))
        for size in range(start, end - 1, -1):
            font = load_font(sources[role], size)
            boxes = [draw.textbbox(pos, line, font=font, anchor="lt")
                     for pos, line in zip(positions, lines)]
            if all(box[0] >= 0 and box[1] >= 0 and box[2] <= image.width and box[3] <= image.height
                   and box[2] - box[0] <= max_width for box in boxes):
                break
        else:
            raise ValueError(f"{kind} does not fit the canvas / text_width, even at {end}px. "
                             "Shorten the text or adjust layout coordinates/text_width/font sizes.")
        for i, box in enumerate(boxes):
            for other_name, other in occupied:
                if box[0] < other[2] and box[2] > other[0] and box[1] < other[3] and box[3] > other[1]:
                    raise ValueError(f"{kind} overlaps {other_name}; adjust layout coordinates or font sizes")
            occupied.append((f"{kind}[{i}]", box))
        for pos, line in zip(positions, lines):
            draw.text(pos, line, font=font, fill=colors[kind], anchor="lt")
        report[kind] = {"font_size_px": size, "font": str(sources[role][0]),
                        "font_index": sources[role][1], "bounds": boxes}

    def point(key):
        x, y = vector(layout[key], 2, f"layout.{key}")
        return round(x * sx), round(y * sy)

    if kicker:
        block("kicker", [kicker], [point("kicker_xy")], "body")
        if layout["accent_line"] is not None:
            line = vector(layout["accent_line"], 4, "layout.accent_line")
            xy = [round(v * (sx if i % 2 == 0 else sy)) for i, v in enumerate(line)]
            if not (0 <= xy[0] < image.width and 0 <= xy[2] < image.width
                    and 0 <= xy[1] < image.height and 0 <= xy[3] < image.height):
                raise ValueError("layout.accent_line must stay inside the canvas")
            stroke = max(1, round(number(layout["accent_width"], "layout.accent_width", 1) * font_scale))
            draw.line(xy, fill=colors["accent"], width=stroke)
    if title:
        x, y = point("title_xy")
        gap = number(layout["title_line_gap"], "layout.title_line_gap", 1) * sy
        block("title", title, [(x, round(y + i * gap)) for i in range(len(title))], "title")
    if subtitle:
        block("subtitle", [subtitle], [point("subtitle_xy")], "body")
    return image, report


def render(config_path, output_dir):
    config_path = config_path.expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object")
    known = {"photo", "stem", "size", "crop_box", "focus", "brightness", "overlay_opacity",
             "kicker", "title", "subtitle", "font_path", "font_index", "layout", "colors"}
    if set(config) - known:
        raise ValueError(f"Unknown config fields: {', '.join(sorted(set(config) - known))}")
    stem = config.get("stem", "photo-cover")
    if not isinstance(stem, str) or not stem.strip() or stem in (".", "..") or "/" in stem or "\\" in stem:
        raise ValueError("stem must be a non-empty filename without path separators")
    size = vector(config.get("size", [2350, 1000]), 2, "size")
    if any(v < 1 or v != int(v) or v > 20000 for v in size):
        raise ValueError("size must contain integer dimensions in [1, 20000]")
    size = tuple(int(v) for v in size)
    layout_updates, color_updates = config.get("layout", {}), config.get("colors", {})
    if not isinstance(layout_updates, dict) or set(layout_updates) - set(LAYOUT):
        raise ValueError(f"layout supports: {', '.join(LAYOUT)}")
    if not isinstance(color_updates, dict) or set(color_updates) - set(COLORS):
        raise ValueError(f"colors supports: {', '.join(COLORS)}")
    layout = {**LAYOUT, **layout_updates}
    colors = {key: ImageColor.getrgb(value) for key, value in {**COLORS, **color_updates}.items()}
    source, clean = prepare_photo(config, config_path.parent, size)
    cover, typography = typeset(clean, config, config_path.parent, layout, colors)
    output_dir = output_dir.expanduser().resolve()
    paths = [output_dir / f"{stem}-{variant}{suffix}"
             for variant in ("clean", "cover") for suffix in (".jpg", ".png", "-mobile.jpg")]
    if any(p.resolve() == source or (p.exists() and p.samefile(source)) for p in paths):
        raise ValueError("An output path would overwrite the source photograph; change stem or output-dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    for variant, image in (("clean", clean), ("cover", cover)):
        image.save(output_dir / f"{stem}-{variant}.jpg", quality=96, subsampling=0)
        image.save(output_dir / f"{stem}-{variant}.png")
        mobile = image.resize((470, max(1, round(image.height * 470 / image.width))), Image.Resampling.LANCZOS)
        mobile.save(output_dir / f"{stem}-{variant}-mobile.jpg", quality=92)
    return {"size": list(size), "source": str(source), "files": [str(p) for p in paths], "typography": typography}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Example JSON:\n  {"photo":"assets/photo.jpg","stem":"city","title":["看清脉络","把工作做完"],\n'
               '   "kicker":"产品实测","subtitle":"从资料到交付","focus":[0.5,0.6],\n'
               '   "overlay_opacity":0.3,"layout":{"title_font_size":118}}\n\n'
               'crop_box is [left,top,right,bottom] in EXIF-oriented source pixels;\n'
               'its region is fitted without stretching. font_path is local and\n'
               'font_index is an integer or {"title":2,"body":0}. Set layout.accent_line\n'
               'to null to omit the kicker underline. Clean files have no overlay/text.')
    parser.add_argument("--config", required=True, type=Path, help="Local JSON configuration")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for six JPG/PNG outputs")
    args = parser.parse_args()
    try:
        print(json.dumps(render(args.config, args.output_dir), ensure_ascii=False, indent=2))
    except (ValueError, OSError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
