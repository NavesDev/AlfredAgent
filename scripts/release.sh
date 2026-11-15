#!/usr/bin/env bash
# Cuts a release: bumps every version, turns "Não lançado" in CHANGELOG.md into the new
# version, commits `chore(release): vX.Y.Z` and creates an annotated tag. Never pushes.
# Usage: release.sh X.Y.Z        cut the release (on a clean main)
#        release.sh notes X.Y.Z  print that version's CHANGELOG section (GitHub release notes)
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
cd "$ROOT"
die() { echo "release: $*" >&2; exit 1; }
semver() { [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] || die "not semver: $1"; }

notes() {
  awk -v v="$1" '
    /^## \[/ { if (on) exit; on = index($0, "## [" v "]") == 1; next }
    on' CHANGELOG.md | sed -e '/./,$!d' -e '/^\[.*\]: /d' -e :a -e '/^\n*$/{$d;N;ba' -e '}'
}

if [[ "${1:-}" == notes ]]; then
  semver "${2:-}"
  out="$(notes "$2")"
  [[ -n "$out" ]] || die "no CHANGELOG section for $2"
  printf '%s\n' "$out"
  exit 0
fi

VERSION="${1:-}"
semver "$VERSION"
TAG="v$VERSION"
[[ "$(git branch --show-current)" == main ]] || die "release from main"
[[ -z "$(git status --porcelain)" ]] || die "working tree is not clean"
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null && die "$TAG already exists"
grep -q '^## \[Não lançado\]' CHANGELOG.md || die 'CHANGELOG.md has no "## [Não lançado]" section'
[[ -n "$(notes 'Não lançado' | tr -d '[:space:]')" ]] || die '"Não lançado" is empty'

# One version for the whole repo.
sed -i "0,/^version = \".*\"/s//version = \"$VERSION\"/" server/pyproject.toml apps/desktop/src-tauri/Cargo.toml
sed -i "0,/\"version\": \".*\"/s//\"version\": \"$VERSION\"/" apps/web/package.json apps/desktop/src-tauri/tauri.conf.json
(cd server && uv lock -q)
(cd apps/desktop/src-tauri && cargo update -q -p alfred-desktop --offline)

today="$(date +%F)"
repo="$(git remote get-url origin | sed -E 's#^git@github.com:#https://github.com/#; s#\.git$##')"
prev="$(git describe --tags --abbrev=0 2>/dev/null || true)"
sed -i "s/^## \[Não lançado\]$/## [Não lançado]\n\n## [$VERSION] - $today/" CHANGELOG.md
sed -i "/^\[Não lançado\]: /d" CHANGELOG.md
link="[$VERSION]: $repo/${prev:+compare/$prev...$TAG}"
[[ -n "$prev" ]] || link="[$VERSION]: $repo/releases/tag/$TAG"
printf '[Não lançado]: %s/compare/%s...HEAD\n%s\n' "$repo" "$TAG" "$link" >>CHANGELOG.md

git add CHANGELOG.md server/pyproject.toml server/uv.lock apps/web/package.json \
  apps/desktop/src-tauri/Cargo.toml apps/desktop/src-tauri/Cargo.lock apps/desktop/src-tauri/tauri.conf.json
git commit -q -m "chore(release): $TAG"
git tag -a "$TAG" -m "Alfred $TAG"

cat <<EOF
Release $TAG pronta (commit + tag locais). Para publicar:
  git push origin main $TAG
  gh release create $TAG --title "Alfred $TAG" --notes "\$(scripts/release.sh notes $VERSION)"
EOF
