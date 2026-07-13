"""Colorblind-distinctness metrics for terminal palettes.

A terminal palette can clear WCAG contrast on its background and still be
useless to a colorblind reader: ANSI red (errors) and ANSI green (success)
collapse to the same hue under deuteranopia, the most common form
(~6% of men).  A theme that signals state by color must keep those slots
perceptually apart under simulated colorblind vision, not just under normal
trichromacy.

This module simulates dichromat vision with the Machado, Oliveira & Fielding
(2009) matrices (severity 1.0), applied in linear-light RGB, and measures
separation with CIEDE2000 in CIELAB.  It is the single source of truth for
the terminal colorblind gate in check-scheme-contrast.py and for the palette
design scripts.
"""
import math

# Machado, Oliveira & Fielding (2009) severity-1.0 dichromacy matrices,
# applied to linear-light RGB.  IEEE TVCG 15(6).
CB_MATRICES = {
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
}


def _srgb_to_linear(component):
    component /= 255.0
    if component <= 0.04045:
        return component / 12.92
    return ((component + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(value):
    value = max(0.0, min(1.0, value))
    if value <= 0.0031308:
        srgb = value * 12.92
    else:
        srgb = 1.055 * value ** (1 / 2.4) - 0.055
    return srgb * 255.0


def simulate(rgb, kind):
    """Return the color an observer with `kind` dichromacy perceives for the
    given sRGB triple, as an sRGB triple.  `kind` is a key of CB_MATRICES."""
    linear = [_srgb_to_linear(channel) for channel in rgb]
    matrix = CB_MATRICES[kind]
    out = []
    for row in matrix:
        out.append(sum(coefficient * linear[i] for i, coefficient in enumerate(row)))
    return tuple(_linear_to_srgb(value) for value in out)


def _linear_to_xyz(linear_rgb):
    red, green, blue = linear_rgb
    x = red * 0.4124564 + green * 0.3575761 + blue * 0.1804375
    y = red * 0.2126729 + green * 0.7151522 + blue * 0.0721750
    z = red * 0.0193339 + green * 0.1191920 + blue * 0.9503041
    return x, y, z


def rgb_to_lab(rgb):
    linear = [_srgb_to_linear(channel) for channel in rgb]
    x, y, z = _linear_to_xyz(linear)
    # D65 reference white.
    x, y, z = x / 0.95047, y / 1.0, z / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def ciede2000(lab1, lab2):
    """CIEDE2000 color difference between two CIELAB triples."""
    light1, a1, b1 = lab1
    light2, a2, b2 = lab2
    avg_light = (light1 + light2) / 2
    chroma1 = math.hypot(a1, b1)
    chroma2 = math.hypot(a2, b2)
    avg_chroma = (chroma1 + chroma2) / 2

    g = 0.5 * (1 - math.sqrt(avg_chroma ** 7 / (avg_chroma ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + g), a2 * (1 + g)
    chroma1p, chroma2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    avg_chromap = (chroma1p + chroma2p) / 2

    def hue(ap, bp):
        if ap == 0 and bp == 0:
            return 0.0
        angle = math.degrees(math.atan2(bp, ap))
        return angle + 360 if angle < 0 else angle

    hue1p, hue2p = hue(a1p, b1), hue(a2p, b2)

    delta_lightp = light2 - light1
    delta_chromap = chroma2p - chroma1p
    if chroma1p * chroma2p == 0:
        delta_huep = 0.0
    elif abs(hue2p - hue1p) <= 180:
        delta_huep = hue2p - hue1p
    elif hue2p - hue1p > 180:
        delta_huep = hue2p - hue1p - 360
    else:
        delta_huep = hue2p - hue1p + 360
    delta_bigh = 2 * math.sqrt(chroma1p * chroma2p) * math.sin(math.radians(delta_huep) / 2)

    if chroma1p * chroma2p == 0:
        avg_huep = hue1p + hue2p
    elif abs(hue1p - hue2p) <= 180:
        avg_huep = (hue1p + hue2p) / 2
    elif hue1p + hue2p < 360:
        avg_huep = (hue1p + hue2p + 360) / 2
    else:
        avg_huep = (hue1p + hue2p - 360) / 2

    t = (
        1
        - 0.17 * math.cos(math.radians(avg_huep - 30))
        + 0.24 * math.cos(math.radians(2 * avg_huep))
        + 0.32 * math.cos(math.radians(3 * avg_huep + 6))
        - 0.20 * math.cos(math.radians(4 * avg_huep - 63))
    )
    sl = 1 + (0.015 * (avg_light - 50) ** 2) / math.sqrt(20 + (avg_light - 50) ** 2)
    sc = 1 + 0.045 * avg_chromap
    sh = 1 + 0.015 * avg_chromap * t
    delta_theta = 30 * math.exp(-(((avg_huep - 275) / 25) ** 2))
    rc = 2 * math.sqrt(avg_chromap ** 7 / (avg_chromap ** 7 + 25 ** 7))
    rt = -rc * math.sin(math.radians(2 * delta_theta))

    return math.sqrt(
        (delta_lightp / sl) ** 2
        + (delta_chromap / sc) ** 2
        + (delta_bigh / sh) ** 2
        + rt * (delta_chromap / sc) * (delta_bigh / sh)
    )


# ANSI slots that must stay mutually distinct: the six chromatic colors
# (red green yellow blue magenta cyan) carry terminal semantics, so a
# colorblind reader must be able to tell them apart.  Black and white are
# separated by luminance and excluded from the chromatic distinctness test.
CHROMATIC_SLOTS = (1, 2, 3, 4, 5, 6)


def palette_report(ansi_colors):
    """Given ANSI slots 0-7 as sRGB triples, return per-vision minimum
    pairwise CIEDE2000 among the chromatic slots and the specific red-green
    separation.  Keys: 'normal', 'deuteranopia', 'protanopia'; each maps to
    (min_delta, worst_pair, red_green_delta)."""
    report = {}
    for vision in ("normal", "deuteranopia", "protanopia"):
        def seen(slot):
            rgb = ansi_colors[slot]
            return rgb if vision == "normal" else simulate(rgb, vision)

        labs = {slot: rgb_to_lab(seen(slot)) for slot in CHROMATIC_SLOTS}
        min_delta = math.inf
        worst = None
        slots = list(CHROMATIC_SLOTS)
        for i, slot_a in enumerate(slots):
            for slot_b in slots[i + 1:]:
                delta = ciede2000(labs[slot_a], labs[slot_b])
                if delta < min_delta:
                    min_delta, worst = delta, (slot_a, slot_b)
        red_green = ciede2000(labs[1], labs[2])
        report[vision] = (min_delta, worst, red_green)
    return report
