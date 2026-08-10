#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
SKILLS_DIR="/mnt/c/Users/Choyeon/.cursor/skills"

install_skill() {
	local name="$1"
	local namespace="$2"
	echo "=== Installing ${name} (${namespace}) ==="
	skillhub install "${name}" --namespace "${namespace}" --dir "${SKILLS_DIR}" || true
	echo
}

install_skill nuxt nuxt
install_skill nuxt-ui nuxt
install_skill vue ivangdavila
install_skill tailwindcss ivangdavila
install_skill typescript ivangdavila
install_skill web-design wpank
install_skill biome-config-validator charlie-morrison

echo "Done."
