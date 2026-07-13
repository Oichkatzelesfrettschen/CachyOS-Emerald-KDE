#!/bin/sh
# Build the Emerald Xcursor theme from Bibata's GPL-3.0 SVG sources.
#
# Bibata ships placeholder-colored SVGs plus an X11 ctgen manifest; this
# recolors the placeholders to the Emerald palette, rasterizes every frame
# (the wait/left_ptr_watch animations are symlinked group dirs, so the tree
# walk follows symlinks), and packages the set with ctgen.  See
# cursors/ATTRIBUTION for the derivative-work notice.
#
# Usage: build-emerald-cursor.sh <bibata-src-dir> <output-dir>
set -eu

bibata_src="${1:?bibata source dir required}"
out_dir="${2:?output dir required}"

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_root="$(dirname -- "$script_dir")"

# Single source of truth shared with scripts/check-scheme-contrast.py.
. "$repo_root/cursors/emerald-palette.conf"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/svg" "$work/bitmaps"

# Swap Bibata's three color sentinels for the Emerald palette.  -L follows
# the symlinked animation directories so all 54-frame sequences are included.
find -L "$bibata_src/svg/modern" -name '*.svg' | while read -r svg; do
    sed -e "s/#00FF00/$BODY/gI" \
        -e "s/#FF0000/$SECONDARY/gI" \
        -e "s/#0000FF/$EDGE/gI" \
        "$svg" > "$work/svg/$(basename "$svg")"
done

# Rasterize at the SVG's native 256px canvas; ctgen downscales per size.
for svg in "$work/svg"/*.svg; do
    rsvg-convert -w 256 -h 256 "$svg" -o "$work/bitmaps/$(basename "${svg%.svg}").png"
done

# ctgen writes cursor symlinks without clobbering; a stale theme dir from a
# prior build (makepkg keeps srcdir across -f runs) collides, so start clean.
rm -rf "$out_dir/Emerald"
mkdir -p "$out_dir"

ctgen "$bibata_src/configs/normal/x.build.toml" \
    -d "$work/bitmaps" \
    -o "$out_dir" \
    -n Emerald \
    -c "Emerald cursor derived from Bibata (GPL-3.0), recolored to the CachyOS Emerald palette" \
    -p x11

# ctgen names the output directory after the theme; confirm the default
# cursor landed, since apps requesting "default" break without it.
test -e "$out_dir/Emerald/cursors/default" \
    || { echo "build-emerald-cursor: no default cursor produced" >&2; exit 1; }
