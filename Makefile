# Build and housekeeping entry points for the CachyOS Emerald KDE theme.
#
# makepkg drives the actual package build (see PKGBUILD); these targets wrap it
# so the repo has a conventional `make` / `make clean` surface and a single
# place that names every regenerable artifact.  Everything `clean` and
# `distclean` remove is also listed in .gitignore, so a clean tree and a clean
# working directory stay in agreement.

PKGNAME := cachyos-emerald-kde-theme-git
MAKEPKG ?= makepkg
PYTHON  ?= python3

# makepkg leaves two kinds of regenerable state behind: per-build working trees
# (pkg/, src/) and the VCS source mirrors it clones once and refetches into
# (bibata/, and a mirror named after the package).  Python bytecode is the only
# other generated tree in the repo.
WORKDIRS   := pkg src
VCSMIRRORS := bibata $(PKGNAME)
PYCACHE    := scripts/__pycache__

.DEFAULT_GOAL := help

.PHONY: help build install check schemes clean distclean

help: ## Show this help
	@echo "Targets:"
	@grep -E '^[a-z][a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| sed -E 's/^([a-z][a-zA-Z_-]+):.*## /  \1\t/' \
		| sort

build: ## Build the package with makepkg (force rebuild)
	$(MAKEPKG) -f

install: ## Build and install the package (makepkg -fi)
	$(MAKEPKG) -fi

check: ## Run the theme validators and linters (read-only)
	scripts/validate-plasma6-theme.sh
	shellcheck -S error scripts/validate-plasma6-theme.sh scripts/build-emerald-cursor.sh
	$(PYTHON) scripts/check-scheme-contrast.py

schemes: ## Regenerate the Konsole color schemes from the shared base
	$(PYTHON) scripts/gen-konsole-schemes.py

clean: ## Remove makepkg working trees and Python bytecode
	rm -rf $(WORKDIRS) $(PYCACHE)

distclean: clean ## Also remove VCS source mirrors and built packages
	rm -rf $(VCSMIRRORS)
	rm -f -- *.pkg.tar* *.src.tar*
