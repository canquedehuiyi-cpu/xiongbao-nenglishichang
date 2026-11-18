#!/bin/sh
# Copyright (c) 2026 Huawei Device Co., Ltd.
# SPDX-License-Identifier: MIT
set -eu

project=${1:?"Usage: $0 <project-directory> <sandbox-home> <node-executable>"}
profile="$project/build-profile.json5"
sandbox=${2:?"Usage: $0 <project-directory> <sandbox-home> <node-executable>"}
shared_root='/storage/Users/currentUser/.ohos/config'
node_executable=${3:?"Usage: $0 <project-directory> <sandbox-home> <node-executable>"}

cp -p "$profile" "$profile.pre-shared-signing.bak"
mkdir -p "$shared_root"
shared=$(mktemp -d "$shared_root/deveco-cli-signing.XXXXXX")
for suffix in p12 csr cer p7b; do
  cp -p "$sandbox/.ohos/config"/default_*."$suffix" "$shared/"
done
cp -R "$sandbox/.ohos/config/material" "$shared/"

"$node_executable" - "$profile" "$sandbox/.ohos/config" "$shared" <<'NODE'
const fs = require('node:fs');
const [file, oldPrefix, newPrefix] = process.argv.slice(2);
const keys = ['certpath', 'profile', 'storeFile'];
const isSigningPath = (line) =>
  keys.some((key) => new RegExp(`["']?${key}["']?\\s*:`).test(line));
const text = fs.readFileSync(file, 'utf8');
const updated = text
  .split('\n')
  .map((line) => (isSigningPath(line) ? line.split(oldPrefix).join(newPrefix) : line))
  .join('\n');
fs.writeFileSync(file, updated);
if (updated.includes(oldPrefix)) {
  console.error('[shared-signing] signing paths still point at the sandbox: ' + oldPrefix);
  process.exit(1);
}
NODE

rm -f "$profile.pre-shared-signing.bak"
