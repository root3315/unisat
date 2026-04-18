#!/usr/bin/env bash
# =============================================================================
#  UniSat — apply Docker base-image digest pin to docker/Dockerfile.ci
#
#  The default `docker/Dockerfile.ci` uses `FROM gcc:13` (tag-based).
#  This script:
#
#    1. pulls gcc:13 from Docker Hub,
#    2. extracts the canonical SHA-256 digest via `docker inspect`,
#    3. rewrites the FROM line in place to `FROM gcc:13@sha256:<digest>`,
#    4. prints a CHANGELOG-ready note the caller can paste.
#
#  This is the "release-engineering toggle" documented at the top of
#  the Dockerfile.  The tag-based default stays in git for the
#  fresh-clone path; a release build runs this script to tighten the
#  supply chain.
#
#  Usage
#  -----
#    scripts/pin_docker.sh           # pin to current gcc:13 on Docker Hub
#    scripts/pin_docker.sh gcc:13.3  # pin a specific tag
#    scripts/pin_docker.sh --unpin   # revert to the tag-only FROM line
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
DOCKERFILE="$ROOT/docker/Dockerfile.ci"

IMAGE="${1:-gcc:13}"

if [[ "$1" == "--unpin" || "${1:-}" == "--unpin" ]]; then
    echo "==> unpinning — reverting Dockerfile.ci to tag-only FROM"
    sed -i -E 's|^FROM gcc:13@sha256:[a-f0-9]+|FROM gcc:13|' "$DOCKERFILE"
    grep '^FROM ' "$DOCKERFILE"
    exit 0
fi

if ! command -v docker >/dev/null; then
    echo "ERROR: docker CLI not available on PATH." >&2
    echo "       Pin cannot be applied automatically on this host." >&2
    echo "       Manual steps (documented in Dockerfile.ci):" >&2
    echo "         1. docker pull $IMAGE" >&2
    echo "         2. docker inspect --format='{{index .RepoDigests 0}}' $IMAGE" >&2
    echo "         3. edit docker/Dockerfile.ci FROM line to use @sha256:<digest>" >&2
    exit 2
fi

echo "==> pulling $IMAGE"
docker pull "$IMAGE" >/dev/null

echo "==> extracting digest"
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$IMAGE" \
         | awk -F'@' '{print $2}')

if [[ -z "$DIGEST" ]] || [[ "$DIGEST" != sha256:* ]]; then
    echo "ERROR: could not determine digest for $IMAGE" >&2
    echo "       inspect output: $(docker inspect --format='{{json .RepoDigests}}' $IMAGE)" >&2
    exit 3
fi

echo "    digest = $DIGEST"

echo "==> rewriting docker/Dockerfile.ci"
sed -i -E "s|^FROM gcc:13(@sha256:[a-f0-9]+)?|FROM gcc:13@${DIGEST}|" "$DOCKERFILE"

grep -n "^FROM " "$DOCKERFILE"

TODAY=$(date -u +"%Y-%m-%d")
cat <<EOF

==> done. CHANGELOG.md note:

   ## Docker pin (${TODAY})

   * base image pinned to \`gcc:13@${DIGEST}\`
   * verification: docker pull gcc:13; docker inspect gcc:13
   * unpin (if digest is rotated out): scripts/pin_docker.sh --unpin

EOF
