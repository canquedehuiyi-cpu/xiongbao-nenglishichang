const RELEASE_VERSION_PATTERN = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-rc\.(0|[1-9]\d*))?$/u;

/** 解析项目支持的正式版和 RC 版本；不接受范围、其他标签或超出安全整数的分量。 */
export function parseReleaseVersion(value) {
  if (typeof value !== "string") return null;
  const match = RELEASE_VERSION_PATTERN.exec(value);
  if (!match) return null;
  const parts = match.slice(1).map((part) => part === undefined ? undefined : Number(part));
  if (parts.some((part) => part !== undefined && !Number.isSafeInteger(part))) return null;
  return { major: parts[0], minor: parts[1], patch: parts[2], prerelease: parts[3] };
}

export function assertReleaseVersion(value, { allowPrerelease = true, label = "版本" } = {}) {
  const parsed = parseReleaseVersion(value);
  if (!parsed || (!allowPrerelease && parsed.prerelease !== undefined)) {
    throw new Error(`${label}格式无效：${String(value)}。只支持 X.Y.Z${allowPrerelease ? " 或 X.Y.Z-rc.N" : ""}，且数字必须为安全整数。`);
  }
  return parsed;
}

/** 比较正式版与 RC；同一主次补丁下，正式版高于任一 RC。 */
export function compareReleaseVersions(left, right) {
  const a = assertReleaseVersion(left);
  const b = assertReleaseVersion(right);
  for (const key of ["major", "minor", "patch"]) {
    if (a[key] !== b[key]) return a[key] < b[key] ? -1 : 1;
  }
  if (a.prerelease === b.prerelease) return 0;
  if (a.prerelease === undefined) return 1;
  if (b.prerelease === undefined) return -1;
  return a.prerelease < b.prerelease ? -1 : 1;
}

export function assertSkillMcpCompatibility(compatibility, mcpVersion) {
  const minimum = assertReleaseVersion(compatibility?.minimumVersion, { label: "Skill 最低 MCP 版本" });
  const actual = assertReleaseVersion(mcpVersion, { label: "MCP 版本" });
  if (!Number.isSafeInteger(compatibility?.allowedMajor) || compatibility.allowedMajor < 0) {
    throw new Error("Skill allowedMajor 必须是非负安全整数。");
  }
  if (compatibility.allowedMajor !== minimum.major) {
    throw new Error("Skill allowedMajor 必须等于最低 MCP 版本的主版本。");
  }
  return actual.major === compatibility.allowedMajor && compareReleaseVersions(mcpVersion, compatibility.minimumVersion) >= 0;
}
