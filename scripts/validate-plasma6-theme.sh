#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
wallpaper_path=/usr/share/wallpapers/cachyos-wallpapers/CachyOS_GreenSpace.png

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "missing required command: $1" >&2
        exit 1
    fi
}

require_command jq
require_command kpackagetool6
require_command qmllint

if [ ! -f "$wallpaper_path" ]; then
    echo "missing wallpaper: $wallpaper_path" >&2
    echo "install the cachyos-wallpapers package before validating this theme" >&2
    exit 1
fi

find "$repo_root/plasma" -name metadata.json -exec jq empty {} +

# KF6 KPackage reads KPackageStructure; ServiceTypes and X-Plasma-MainScript are
# dead KF5 keys and their presence marks a package that predates the port.
find "$repo_root/plasma" -name metadata.json | while IFS= read -r metadata_file; do
    if jq -e '.KPlugin.ServiceTypes // .["X-Plasma-MainScript"]' "$metadata_file" >/dev/null 2>&1; then
        echo "deprecated KF5 metadata key in: $metadata_file" >&2
        exit 1
    fi
done

# KSvg resolves foo.svgz before foo.svg, so a .svgz must be real gzip and a
# .svg sibling of the same stem is unreachable dead weight (or worse, the
# intended asset shadowed by a stray copy).
find "$repo_root/plasma" -name '*.svgz' | while IFS= read -r svgz_file; do
    if ! gzip -t "$svgz_file" 2>/dev/null; then
        echo "not gzip data: $svgz_file" >&2
        exit 1
    fi
    svg_sibling="${svgz_file%.svgz}.svg"
    if [ -e "$svg_sibling" ]; then
        echo "svg shadowed by svgz sibling: $svg_sibling" >&2
        exit 1
    fi
done

# Filenames with spaces or parentheses are download-manager duplicates.
if find "$repo_root/plasma" -name '* *' -o -name '*(*' | grep .; then
    echo "junk filename detected above" >&2
    exit 1
fi

qmllint "$repo_root/plasma/look-and-feel/com.github.rkstrdee.emerald/contents/splash/Splash.qml"

tmp_data_home=$(mktemp -d)
trap 'rm -rf "$tmp_data_home"' EXIT HUP INT TERM

XDG_DATA_HOME=$tmp_data_home \
    kpackagetool6 --type Plasma/LookAndFeel \
    --install "$repo_root/plasma/look-and-feel/com.github.rkstrdee.emerald" >/dev/null

for theme_name in cachyos-emerald cachyos-emerald-color cachyos-emerald-light; do
    XDG_DATA_HOME=$tmp_data_home \
        kpackagetool6 --type Plasma/Theme \
        --install "$repo_root/plasma/desktoptheme/$theme_name" >/dev/null
done

echo "Plasma 6 theme validation passed"
