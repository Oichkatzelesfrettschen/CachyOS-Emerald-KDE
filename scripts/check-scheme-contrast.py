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
DARK_SCHEMES = ("EmeraldDark", "EmeraldDarker")
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


def main():
    all_ok = True
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
