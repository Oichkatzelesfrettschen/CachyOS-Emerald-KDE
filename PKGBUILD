# Maintainer: Eirikr <eirikr@users.noreply.github.com>

pkgname=cachyos-emerald-kde-theme-git
pkgver=r27.4dfd0ca
pkgrel=1
pkgdesc="CachyOS Emerald KDE Theme"
arch=('any')
url="https://github.com/Oichkatzelesfrettschen/CachyOS-Emerald-KDE"
license=('GPL-3.0-only')
groups=('cachyos')
depends=('cachyos-wallpapers' 'char-white' 'qt6-declarative')
makedepends=('git' 'jq' 'kpackage' 'shellcheck')
optdepends=('plasma-desktop: for the included Plasma global and desktop themes')
source=("${pkgname}::git+${url}.git#branch=main")
sha256sums=('SKIP')

pkgver() {
    cd "${srcdir}/${pkgname}"
    printf 'r%s.%s' "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

check() {
    cd "${srcdir}/${pkgname}"
    scripts/validate-plasma6-theme.sh
    shellcheck -S error scripts/validate-plasma6-theme.sh
}

package() {
    cd "${srcdir}/${pkgname}"

    install -dm755 "${pkgdir}/usr/share/color-schemes"
    cp -a color-schemes/. "${pkgdir}/usr/share/color-schemes/"

    install -dm755 "${pkgdir}/usr/share/plasma/desktoptheme"
    cp -a plasma/desktoptheme/. "${pkgdir}/usr/share/plasma/desktoptheme/"

    install -dm755 "${pkgdir}/usr/share/plasma/look-and-feel"
    cp -a plasma/look-and-feel/. "${pkgdir}/usr/share/plasma/look-and-feel/"

    install -Dm755 scripts/validate-plasma6-theme.sh \
        "${pkgdir}/usr/share/doc/${pkgname}/validate-plasma6-theme.sh"
}
