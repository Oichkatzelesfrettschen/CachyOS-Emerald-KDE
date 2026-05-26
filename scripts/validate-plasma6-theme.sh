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
