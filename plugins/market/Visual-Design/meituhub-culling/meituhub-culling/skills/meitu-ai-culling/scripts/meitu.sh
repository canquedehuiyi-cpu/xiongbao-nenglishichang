#!/bin/sh
# Node-independent launcher. Only this process uses the private runtime.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
version=22.23.4
valid_node() {
  "$1" -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>20||(a===20&&b>=5)?0:1)' >/dev/null 2>&1
}
if command -v node >/dev/null 2>&1 && valid_node "$(command -v node)"; then
  exec "$(command -v node)" "$script_dir/meitu.cjs" "$@"
fi
case "$(uname -s)" in Darwin) platform=darwin;; Linux) platform=linux;; *) echo 'Unsupported operating system for automatic Node preparation' >&2; exit 2;; esac
case "$(uname -m)" in arm64|aarch64) arch=arm64;; x86_64|amd64) arch=x64;; *) echo 'Unsupported CPU architecture for automatic Node preparation' >&2; exit 2;; esac
variant="$platform-$arch"
if [ "$platform" = linux ] && { ls /lib/ld-musl-*.so.1 >/dev/null 2>&1 || ldd --version 2>&1 | grep -qi musl; }; then
  [ "$arch" = x64 ] || { echo 'Automatic Node preparation does not support Linux musl arm64' >&2; exit 2; }
  variant="$variant-musl"
fi
case "$variant" in
  darwin-arm64) checksum=c9e1dbc748b33ed2d14f42445191ecaf14c56259c7a9a26d0042c49ec2b66428;;
  darwin-x64) checksum=efcc2b0db6f94bf53eddb038fe2b370277a042bd29e4f19b8f8e23598795b819;;
  linux-arm64) checksum=f7a1e486dbc8b286847815b477d4fb5e9fb963ed4489c3e1588853d685f589f9;;
  linux-x64) checksum=b8492284c76a54baf58d61668dd0e41ee0fc98adabf9503d30f05d08f55b4406;;
  linux-x64-musl) checksum=63189402eaa222aabf51b4983e512592131cd2d4a9efc3ad9bf291fe74e3e4de;;
esac
: "${HOME:?HOME is required for a private runtime}"
root="$HOME/.meituhub-qoder/runtime/tools/node-v$version-$variant"
node="$root/bin/node"
if [ -f "$node" ] && valid_node "$node"; then
  PATH="$root/bin:$PATH"; export PATH
  exec "$node" "$script_dir/meitu.cjs" "$@"
fi
mkdir -p "$root"
lock="$root/install.lock"
waited=0
until mkdir "$lock" 2>/dev/null; do
  if [ "$waited" -ge 60 ]; then echo 'Node preparation is busy; retry later (an interrupted installer may leave install.lock)' >&2; exit 2; fi
  sleep 1; waited=$((waited + 1))
done
stage=''
cleanup() {
  [ -z "$stage" ] || rm -rf -- "$stage"
  rmdir "$lock" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if ! [ -f "$node" ] || ! valid_node "$node"; then
  stage=$(mktemp -d "$root/.prepare.XXXXXX")
  archive="node-v$version-$variant.tar.gz"
  echo 'Preparing a private Node.js runtime…' >&2
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 180 --max-filesize 104857600 "https://nodejs.org/dist/v$version/$archive" -o "$stage/node.tar.gz"
  else
    echo 'Automatic Node preparation requires the system curl download tool' >&2; exit 2
  fi
  if command -v shasum >/dev/null 2>&1; then
    actual=$(shasum -a 256 "$stage/node.tar.gz" | cut -d ' ' -f 1)
  elif command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum "$stage/node.tar.gz" | cut -d ' ' -f 1)
  else
    echo 'No system SHA-256 verification tool available' >&2; exit 2
  fi
  [ "$actual" = "$checksum" ] || { echo 'Node archive SHA-256 mismatch' >&2; exit 2; }
  # Extract only the executable from the pinned, verified official archive.
  tar -xzf "$stage/node.tar.gz" -C "$stage" "node-v$version-$variant/bin/node"
  candidate="$stage/node-v$version-$variant/bin/node"
  [ "$("$candidate" --version)" = "v$version" ] || { echo 'Downloaded Node cannot run on this system' >&2; exit 2; }
  mkdir -p "$root/bin"
  mv -f "$candidate" "$node"
fi
cleanup
stage=''
trap - EXIT INT TERM
PATH="$root/bin:$PATH"; export PATH
exec "$node" "$script_dir/meitu.cjs" "$@"
