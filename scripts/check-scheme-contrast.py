#!/usr/bin/env python3
"""Perceptual gate for the Emerald color schemes.

A KDE color scheme can be structurally valid while visually broken: an
accent that drifted out of the emerald hue band, a focus decoration
below the WCAG 1.4.11 non-text threshold, or zebra rows whose contrast
rounds to 1.0.  This gate measures those properties so a regression
fails the build instead of shipping.

Checks per dark scheme (EmeraldDark, EmeraldDarker):
  - body text on Window/View background  >= 4.5:1  (WCAG 1.4.3)
  - DecorationFocus on Window background >= 3.0:1  (WCAG 1.4.11)
  - Selection background vs View background >= 3.0:1
  - Selection ForegroundNormal on Selection background >= 4.5:1
  - View BackgroundAlternate vs BackgroundNormal >= 1.15:1 (zebra)
  - DecorationFocus and Selection background hue in [130, 180] degrees
    (the emerald band; Nord blue sits near 210, purple near 280)
"""
import colorsys
import configparser
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEME_DIR = REPO_ROOT / "color-schemes"
DARK_SCHEMES = ("EmeraldDark", "EmeraldDarker", "EmeraldSmooth")
EMERALD_HUE_RANGE = (130.0, 180.0)


def srgb_luminance(color):
    def channel(value):
        value /= 255.0
        if value <= 0.03928:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = color
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def contrast_ratio(color_a, color_b):
    lighter, darker = sorted(
        (srgb_luminance(color_a), srgb_luminance(color_b)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def hue_degrees(color):
    hue, _, _ = colorsys.rgb_to_hls(*(component / 255.0 for component in color))
    return hue * 360.0


def parse_color(scheme, section, key):
    raw = scheme[section][key]
    return tuple(int(component) for component in raw.split(",")[:3])


def parse_hex(value):
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def check_scheme(path):
    scheme = configparser.ConfigParser(strict=False)
    scheme.optionxform = str
    scheme.read(path)

    window_bg = parse_color(scheme, "Colors:Window", "BackgroundNormal")
    view_bg = parse_color(scheme, "Colors:View", "BackgroundNormal")
    view_alt = parse_color(scheme, "Colors:View", "BackgroundAlternate")
    window_fg = parse_color(scheme, "Colors:Window", "ForegroundNormal")
    view_fg = parse_color(scheme, "Colors:View", "ForegroundNormal")
    focus = parse_color(scheme, "Colors:Window", "DecorationFocus")
    selection_bg = parse_color(scheme, "Colors:Selection", "BackgroundNormal")
    selection_fg = parse_color(scheme, "Colors:Selection", "ForegroundNormal")

    failures = []

    def require(label, actual, minimum):
        if actual < minimum:
            failures.append(f"{label}: {actual:.2f} < {minimum}")

    require("window text contrast", contrast_ratio(window_fg, window_bg), 4.5)
    require("view text contrast", contrast_ratio(view_fg, view_bg), 4.5)
    require("focus decoration contrast", contrast_ratio(focus, window_bg), 3.0)
    require("selection visibility", contrast_ratio(selection_bg, view_bg), 3.0)
    require("selection text contrast", contrast_ratio(selection_fg, selection_bg), 4.5)
    require("view zebra contrast", contrast_ratio(view_alt, view_bg), 1.15)

    for label, color in (("focus decoration", focus), ("selection background", selection_bg)):
        hue = hue_degrees(color)
        low, high = EMERALD_HUE_RANGE
        if not low <= hue <= high:
            failures.append(f"{label} hue {hue:.0f} outside emerald band [{low:.0f}, {high:.0f}]")

    return failures


LNF_DEFAULTS = (
    "plasma/look-and-feel/com.github.rkstrdee.emerald/contents/defaults",
    "plasma/look-and-feel/com.github.rkstrdee.emerald.darker/contents/defaults",
    "plasma/look-and-feel/com.github.rkstrdee.emerald.smooth/contents/defaults",
)


def check_accent_pin(rel_path):
    """Plasma synthesizes Selection and Decoration roles from AccentColor
    when the key is set in the user's kdeglobals, overriding the scheme.
    A look-and-feel package that omits the key inherits whatever stale
    accent the user last had, so each defaults file must pin an accent
    inside the emerald band."""
    path = REPO_ROOT / rel_path
    accent = None
    for line in path.read_text().splitlines():
        if line.startswith("AccentColor="):
            accent = tuple(int(c) for c in line.split("=", 1)[1].split(",")[:3])
    if accent is None:
        return [f"{rel_path}: no AccentColor pin; stale user accents override the scheme"]
    hue = hue_degrees(accent)
    low, high = EMERALD_HUE_RANGE
    if not low <= hue <= high:
        return [f"{rel_path}: AccentColor hue {hue:.0f} outside emerald band [{low:.0f}, {high:.0f}]"]
    return []


def check_svg_cascade():
    """An inline `color:` declaration on a ColorScheme-classed SVG element
    outranks the KSvg stylesheet class in the CSS cascade, so
    fill:currentColor resolves to the baked-in color instead of the theme
    palette -- a panel silently renders Breeze-light white on a dark theme.
    Reject any element combining a ColorScheme class, currentColor, and an
    inline color declaration."""
    import glob
    import gzip
    import re

    failures = []
    pattern = str(REPO_ROOT / "plasma" / "desktoptheme" / "**" / "*.svg*")
    for path in glob.glob(pattern, recursive=True):
        opener = gzip.open if path.endswith(".svgz") else open
        data = opener(path, "rb").read().decode()
        rel = pathlib.Path(path).relative_to(REPO_ROOT)
        is_background_asset = "panel-background" in path or "/dialogs/" in path
        for match in re.finditer(r"<[a-zA-Z]+[^>]*>", data):
            tag = match.group(0)
            if (
                "ColorScheme-" in tag
                and "currentColor" in tag
                and re.search(r'style="(?:[^"]*;)?color:#', tag)
            ):
                failures.append(f"{rel}: inline color overrides currentColor cascade")
                break
            # KSvg palette injection proved unreliable for panel and dialog
            # backgrounds on Plasma 6.7 (the fallback stylesheet's #eff0f1
            # rendered on screen); Background elements there must carry a
            # concrete fill, the Breeze-Noir-Dark approach.
            if (
                is_background_asset
                and "ColorScheme-Background" in tag
                and "fill:currentColor" in tag
            ):
                failures.append(f"{rel}: Background element relies on palette injection")
                break
    return failures


def check_konsole_schemes():
    """Terminal text must clear WCAG body-text contrast, keep the ANSI green
    slot in the emerald band, and hold the six chromatic slots mutually
    distinct under simulated colorblindness -- an earlier revision collapsed
    green and cyan to CIEDE2000 3.8 (both emerald teals), which reads as
    'not unique' even to normal vision and worse to a dichromat.  The
    colorblind distinctness metric lives in cb_palette."""
    import cb_palette

    failures = []
    for path in sorted((REPO_ROOT / "konsole").glob("*.colorscheme")):
        scheme = configparser.ConfigParser(strict=False)
        scheme.optionxform = str
        scheme.read(path)
        background = parse_color(scheme, "Background", "Color")
        foreground = parse_color(scheme, "Foreground", "Color")
        green = parse_color(scheme, "Color2", "Color")
        ratio = contrast_ratio(foreground, background)
        if ratio < 4.5:
            failures.append(f"{path.name}: terminal text contrast {ratio:.2f} < 4.5")
        hue = hue_degrees(green)
        low, high = EMERALD_HUE_RANGE
        if not low <= hue <= high:
            failures.append(f"{path.name}: ANSI green hue {hue:.0f} outside emerald band")

        ansi = {slot: parse_color(scheme, f"Color{slot}", "Color") for slot in range(8)}
        report = cb_palette.palette_report(ansi)
        normal_min = report["normal"][0]
        if normal_min < 12.0:
            worst = report["normal"][1]
            failures.append(f"{path.name}: chromatic slots {worst} too similar (dE {normal_min:.1f} < 12)")
        for vision in ("deuteranopia", "protanopia"):
            vision_min, worst, red_green = report[vision]
            if vision_min < 9.0:
                failures.append(f"{path.name}: {vision} collapses {worst} (dE {vision_min:.1f} < 9)")
            if red_green < 15.0:
                failures.append(f"{path.name}: {vision} red/green dE {red_green:.1f} < 15")
    return failures


def check_syntax_themes():
    """Editor themes must keep syntax legible on their own background and
    keep the emerald identity in the keyword slot.  Every syntax role
    except the deliberately-dim Comment must clear WCAG AA-large (3:1) on
    the editor background, and the Keyword color must sit in the emerald
    band -- the same monochrome-vs-rainbow discipline as the desktop."""
    import json

    failures = []
    theme_dir = REPO_ROOT / "syntax-highlighting"
    for path in sorted(theme_dir.glob("*.theme")):
        theme = json.loads(path.read_text())
        background = parse_hex(theme["editor-colors"]["BackgroundColor"])
        styles = theme["text-styles"]
        for role, style in styles.items():
            if role == "Comment":
                continue
            ratio = contrast_ratio(parse_hex(style["text-color"]), background)
            if ratio < 3.0:
                failures.append(f"{path.name}: {role} contrast {ratio:.2f} < 3.0")
        keyword_hue = hue_degrees(parse_hex(styles["Keyword"]["text-color"]))
        low, high = EMERALD_HUE_RANGE
        if not low <= keyword_hue <= high:
            failures.append(f"{path.name}: Keyword hue {keyword_hue:.0f} outside emerald band")
    return failures


def check_cursor_palette():
    """The Emerald Xcursor recolor map (cursors/emerald-palette.conf) is the
    single source of truth shared with scripts/build-emerald-cursor.sh.  The
    pointer body must sit in the emerald band, and the body must clear the
    WCAG 1.4.11 non-text threshold against its own outline so the cursor
    stays a legible shape rather than a flat emerald blob."""
    failures = []
    path = REPO_ROOT / "cursors" / "emerald-palette.conf"
    if not path.is_file():
        return [f"{path}: missing cursor palette manifest"]
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    body = parse_hex(values["BODY"])
    edge = parse_hex(values["EDGE"])
    hue = hue_degrees(body)
    low, high = EMERALD_HUE_RANGE
    if not low <= hue <= high:
        failures.append(f"cursor body hue {hue:.0f} outside emerald band [{low:.0f}, {high:.0f}]")
    ratio = contrast_ratio(body, edge)
    if ratio < 3.0:
        failures.append(f"cursor body/outline contrast {ratio:.2f} < 3.0")
    return failures


def main():
    all_ok = True
    for failure in check_cursor_palette():
        all_ok = False
        print(failure, file=sys.stderr)
    for failure in check_syntax_themes():
        all_ok = False
        print(failure, file=sys.stderr)
    for failure in check_konsole_schemes():
        all_ok = False
        print(failure, file=sys.stderr)
    for failure in check_svg_cascade():
        all_ok = False
        print(failure, file=sys.stderr)
    for rel_path in LNF_DEFAULTS:
        failures = check_accent_pin(rel_path)
        if failures:
            all_ok = False
            for failure in failures:
                print(failure, file=sys.stderr)
        else:
            print(f"{rel_path}: accent pin passed")
    for name in DARK_SCHEMES:
        path = SCHEME_DIR / f"{name}.colors"
        if not path.is_file():
            print(f"{name}: missing scheme file {path}", file=sys.stderr)
            all_ok = False
            continue
        failures = check_scheme(path)
        if failures:
            all_ok = False
            for failure in failures:
                print(f"{name}: {failure}", file=sys.stderr)
        else:
            print(f"{name}: perceptual gate passed")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
