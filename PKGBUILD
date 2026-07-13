# Maintainer: Eirikr <eirikr@users.noreply.github.com>

pkgname=cachyos-emerald-kde-theme-git
pkgver=r44.64f2e7b
pkgrel=1
pkgdesc="CachyOS Emerald KDE Theme"
arch=('any')
url="https://github.com/Oichkatzelesfrettschen/CachyOS-Emerald-KDE"
license=('GPL-3.0-only')
groups=('cachyos')
depends=('cachyos-wallpapers' 'char-white' 'qt6-declarative')
makedepends=('git' 'jq' 'kpackage' 'python' 'python-clickgen' 'librsvg' 'shellcheck')
optdepends=('plasma-desktop: for the included Plasma global and desktop themes')
# The Emerald Xcursor theme is built from Bibata's GPL-3.0 SVG sources,
# pinned to a commit for reproducibility.  See cursors/ATTRIBUTION.
source=("${pkgname}::git+${url}.git#branch=main"
        "bibata::git+https://github.com/ful1e5/Bibata_Cursor.git#commit=35ccfe209a808e40d6c2ca60a46cbe4faf68b690")
sha256sums=('SKIP'
            'SKIP')

pkgver() {
    cd "${srcdir}/${pkgname}"
    printf 'r%s.%s' "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

build() {
    cd "${srcdir}/${pkgname}"
    scripts/build-emerald-cursor.sh "${srcdir}/bibata" "${srcdir}/cursor-out"
}

check() {
    cd "${srcdir}/${pkgname}"
    scripts/validate-plasma6-theme.sh
    shellcheck -S error scripts/validate-plasma6-theme.sh scripts/build-emerald-cursor.sh
}

package() {
    cd "${srcdir}/${pkgname}"

    install -dm755 "${pkgdir}/usr/share/color-schemes"
    cp -a color-schemes/. "${pkgdir}/usr/share/color-schemes/"

    install -dm755 "${pkgdir}/usr/share/plasma/desktoptheme"
    cp -a plasma/desktoptheme/. "${pkgdir}/usr/share/plasma/desktoptheme/"

    install -dm755 "${pkgdir}/usr/share/plasma/look-and-feel"
    cp -a plasma/look-and-feel/. "${pkgdir}/usr/share/plasma/look-and-feel/"

    install -dm755 "${pkgdir}/usr/share/konsole"
    install -m644 konsole/*.colorscheme "${pkgdir}/usr/share/konsole/"

    install -dm755 "${pkgdir}/usr/share/org.kde.syntax-highlighting/themes"
    install -m644 syntax-highlighting/*.theme \
        "${pkgdir}/usr/share/org.kde.syntax-highlighting/themes/"

    install -dm755 "${pkgdir}/usr/share/sddm/themes"
    cp -a sddm/. "${pkgdir}/usr/share/sddm/themes/"

    install -dm755 "${pkgdir}/usr/share/themes"
    cp -a gtk/. "${pkgdir}/usr/share/themes/"

    install -dm755 "${pkgdir}/usr/share/icons"
    cp -a "${srcdir}/cursor-out/Emerald" "${pkgdir}/usr/share/icons/Emerald"
    install -m644 cursors/ATTRIBUTION "${pkgdir}/usr/share/icons/Emerald/ATTRIBUTION"
}
