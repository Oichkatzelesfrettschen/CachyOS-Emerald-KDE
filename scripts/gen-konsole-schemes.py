#!/usr/bin/env python3
"""Generate the Emerald Konsole color schemes from one colorblind-safe base.

The six chromatic ANSI slots are a single shared palette tuned so all six
stay mutually distinct under deuteranopia and protanopia (CIEDE2000 >= ~13),
not merely under normal vision -- the earlier hand-picked schemes collapsed
green and cyan to dE 3.8 because both were emerald teals.  Each scheme varies
only its background, foreground, black/white anchors, and the glass options
(Opacity/Blur); the chromatics stay constant so the whole family shares one
vision-conformant identity.

Emerald Darkest is the synthesis the brief asked for: Modus Vivendi's essence
(maximal contrast on a pure-black canvas) merged with Black Glass's translucent
sheen (Opacity + Blur), carrying the emerald identity.  Emerald Source Console
evokes the Source-engine developer-console mood -- a dark olive canvas with
muted grey-green body text -- as an original palette copying no Valve asset.

Run from the repo root; writes konsole/*.colorscheme and konsole/*.profile.
scripts/check-scheme-contrast.py independently re-verifies every emitted file.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cb_palette as cb

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
KONSOLE_DIR = REPO_ROOT / "konsole"

# Colorblind-safe chromatic base (ANSI 1-6), luminance-laddered so the six
# hues separate by brightness when dichromacy collapses their hue.  Green is
# the emerald identity color; the rest were searched to maximize the minimum
# pairwise CIEDE2000 under simulated deuteranopia and protanopia.
BASE = {
    "red": (240, 85, 61),
    "green": (71, 214, 173),
    "yellow": (242, 192, 103),
    "blue": (76, 127, 238),
    "magenta": (214, 142, 196),
    "cyan": (162, 237, 240),
}
ORDER = ("red", "green", "yellow", "blue", "magenta", "cyan")


def mix(color, target, amount):
    return tuple(round(c + (t - c) * amount) for c, t in zip(color, target))


def faint(color):
    return mix(color, (0, 0, 0), 0.34)


def intense(color):
    return mix(color, (255, 255, 255), 0.30)


def brighten(color, amount):
    return mix(color, (255, 255, 255), amount)


# Each scheme: background, foreground, black (Color0), white (Color7),
# opacity, blur, and a per-scheme chromatic transform (identity by default).
SCHEMES = {
    "EmeraldDark": dict(
        desc="Emerald Dark", bg=(24, 27, 40), fg=(214, 240, 230),
        black=(30, 34, 51), white=(216, 222, 233), opacity=1.0, blur=False,
    ),
    "EmeraldDarker": dict(
        desc="Emerald Darker", bg=(0, 22, 33), fg=(206, 240, 228),
        black=(8, 30, 42), white=(216, 222, 233), opacity=1.0, blur=False,
    ),
    "EmeraldSmooth": dict(
        desc="Emerald Smooth", bg=(26, 28, 32), fg=(214, 240, 230),
        black=(30, 32, 36), white=(216, 222, 233), opacity=1.0, blur=False,
    ),
    # Modus essence (AAA on pure black) + Black Glass (translucent).  The
    # chromatics are brightened so every slot clears 7:1 on #000000.
    "EmeraldDarkest": dict(
        desc="Emerald Darkest", bg=(0, 0, 0), fg=(245, 250, 248),
        black=(24, 24, 24), white=(255, 255, 255), opacity=0.92, blur=True,
        transform=lambda c: brighten(c, 0.18),
    ),
    # Source-engine developer-console mood (an original palette evoking the
    # Valve VGUI2 look -- dark olive canvas, muted grey-green body text -- with
    # no Valve asset copied): named to reference the aesthetic, not the toolkit.
    "EmeraldSourceConsole": dict(
        desc="Emerald Source Console", bg=(20, 23, 17), fg=(178, 188, 168),
        black=(28, 31, 24), white=(210, 216, 196), opacity=1.0, blur=False,
    ),
}

INDENT_KEYS = ("Anchor", "Blur", "ColorRandomization", "Description",
               "FillStyle", "Opacity", "Wallpaper", "WallpaperFlipType",
               "WallpaperOpacity")


def rgb(color):
    return "{},{},{}".format(*color)


def emit_scheme(name, spec):
    transform = spec.get("transform", lambda c: c)
    chroma = {slot: transform(BASE[slot]) for slot in ORDER}

    lines = []

    def section(title, color):
        lines.append(f"[{title}]")
        lines.append(f"Color={rgb(color)}")
        lines.append("")

    section("Background", spec["bg"])
    section("BackgroundFaint", faint(spec["bg"]) if spec["bg"] != (0, 0, 0) else (0, 0, 0))
    section("BackgroundIntense", mix(spec["bg"], (255, 255, 255), 0.06))

    ansi = [spec["black"]] + [chroma[s] for s in ORDER] + [spec["white"]]
    for index, base_color in enumerate(ansi):
        section(f"Color{index}", base_color)
        section(f"Color{index}Faint", faint(base_color))
        section(f"Color{index}Intense", intense(base_color))

    section("Foreground", spec["fg"])
    section("ForegroundFaint", mix(spec["fg"], spec["bg"], 0.30))
    section("ForegroundIntense", mix(spec["fg"], (255, 255, 255), 0.35))

    lines.append("[General]")
    lines.append("Anchor=0.5,0.5")
    lines.append(f"Blur={'true' if spec['blur'] else 'false'}")
    lines.append("ColorRandomization=false")
    lines.append(f"Description={spec['desc']}")
    lines.append("FillStyle=Tile")
    opacity = spec["opacity"]
    lines.append(f"Opacity={opacity:g}")
    lines.append("Wallpaper=")
    lines.append("WallpaperFlipType=NoFlip")
    lines.append("WallpaperOpacity=1")
    lines.append("")

    (KONSOLE_DIR / f"{name}.colorscheme").write_text("\n".join(lines))
    return ansi


def emit_profile(name, spec):
    # A matching profile enabling bold-intense so bold text renders through the
    # scheme's Intense colors, and selecting the scheme.  No font is forced.
    text = (
        "[Appearance]\n"
        f"ColorScheme={name}\n"
        "BoldIntense=true\n"
        "UseFontLineChars=true\n"
        "\n"
        "[General]\n"
        f"Name={spec['desc']}\n"
        "Parent=FALLBACK/\n"
    )
    (KONSOLE_DIR / f"{name}.profile").write_text(text)


def main():
    for name, spec in SCHEMES.items():
        ansi = emit_scheme(name, spec)
        emit_profile(name, spec)
        report = cb.palette_report({i: ansi[i] for i in range(8)})
        deut = report["deuteranopia"][0]
        protan = report["protanopia"][0]
        normal = report["normal"][0]
        print(f"{name:20s} CB-min deut={deut:4.1f} protan={protan:4.1f} normal={normal:4.1f}")
    print(f"wrote {len(SCHEMES)} schemes + profiles to {KONSOLE_DIR}")


if __name__ == "__main__":
    main()
