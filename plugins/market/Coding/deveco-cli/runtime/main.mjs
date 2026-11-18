var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// node_modules/semver/internal/constants.js
var require_constants = __commonJS({
  "node_modules/semver/internal/constants.js"(exports, module) {
    "use strict";
    var SEMVER_SPEC_VERSION = "2.0.0";
    var MAX_LENGTH = 256;
    var MAX_SAFE_INTEGER = Number.MAX_SAFE_INTEGER || /* istanbul ignore next */
    9007199254740991;
    var MAX_SAFE_COMPONENT_LENGTH = 16;
    var MAX_SAFE_BUILD_LENGTH = MAX_LENGTH - 6;
    var RELEASE_TYPES = [
      "major",
      "premajor",
      "minor",
      "preminor",
      "patch",
      "prepatch",
      "prerelease"
    ];
    module.exports = {
      MAX_LENGTH,
      MAX_SAFE_COMPONENT_LENGTH,
      MAX_SAFE_BUILD_LENGTH,
      MAX_SAFE_INTEGER,
      RELEASE_TYPES,
      SEMVER_SPEC_VERSION,
      FLAG_INCLUDE_PRERELEASE: 1,
      FLAG_LOOSE: 2
    };
  }
});

// node_modules/semver/internal/debug.js
var require_debug = __commonJS({
  "node_modules/semver/internal/debug.js"(exports, module) {
    "use strict";
    var debug = typeof process === "object" && process.env && process.env.NODE_DEBUG && /\bsemver\b/i.test(process.env.NODE_DEBUG) ? (...args) => console.error("SEMVER", ...args) : () => {
    };
    module.exports = debug;
  }
});

// node_modules/semver/internal/re.js
var require_re = __commonJS({
  "node_modules/semver/internal/re.js"(exports, module) {
    "use strict";
    var {
      MAX_SAFE_COMPONENT_LENGTH,
      MAX_SAFE_BUILD_LENGTH,
      MAX_LENGTH
    } = require_constants();
    var debug = require_debug();
    exports = module.exports = {};
    var re = exports.re = [];
    var safeRe = exports.safeRe = [];
    var src = exports.src = [];
    var safeSrc = exports.safeSrc = [];
    var t = exports.t = {};
    var R = 0;
    var LETTERDASHNUMBER = "[a-zA-Z0-9-]";
    var safeRegexReplacements = [
      ["\\s", 1],
      ["\\d", MAX_LENGTH],
      [LETTERDASHNUMBER, MAX_SAFE_BUILD_LENGTH]
    ];
    var makeSafeRegex = (value) => {
      for (const [token, max] of safeRegexReplacements) {
        value = value.split(`${token}*`).join(`${token}{0,${max}}`).split(`${token}+`).join(`${token}{1,${max}}`);
      }
      return value;
    };
    var createToken = (name, value, isGlobal) => {
      const safe = makeSafeRegex(value);
      const index = R++;
      debug(name, index, value);
      t[name] = index;
      src[index] = value;
      safeSrc[index] = safe;
      re[index] = new RegExp(value, isGlobal ? "g" : void 0);
      safeRe[index] = new RegExp(safe, isGlobal ? "g" : void 0);
    };
    createToken("NUMERICIDENTIFIER", "0|[1-9]\\d*");
    createToken("NUMERICIDENTIFIERLOOSE", "\\d+");
    createToken("NONNUMERICIDENTIFIER", `\\d*[a-zA-Z-]${LETTERDASHNUMBER}*`);
    createToken("MAINVERSION", `(${src[t.NUMERICIDENTIFIER]})\\.(${src[t.NUMERICIDENTIFIER]})\\.(${src[t.NUMERICIDENTIFIER]})`);
    createToken("MAINVERSIONLOOSE", `(${src[t.NUMERICIDENTIFIERLOOSE]})\\.(${src[t.NUMERICIDENTIFIERLOOSE]})\\.(${src[t.NUMERICIDENTIFIERLOOSE]})`);
    createToken("PRERELEASEIDENTIFIER", `(?:${src[t.NONNUMERICIDENTIFIER]}|${src[t.NUMERICIDENTIFIER]})`);
    createToken("PRERELEASEIDENTIFIERLOOSE", `(?:${src[t.NONNUMERICIDENTIFIER]}|${src[t.NUMERICIDENTIFIERLOOSE]})`);
    createToken("PRERELEASE", `(?:-(${src[t.PRERELEASEIDENTIFIER]}(?:\\.${src[t.PRERELEASEIDENTIFIER]})*))`);
    createToken("PRERELEASELOOSE", `(?:-?(${src[t.PRERELEASEIDENTIFIERLOOSE]}(?:\\.${src[t.PRERELEASEIDENTIFIERLOOSE]})*))`);
    createToken("BUILDIDENTIFIER", `${LETTERDASHNUMBER}+`);
    createToken("BUILD", `(?:\\+(${src[t.BUILDIDENTIFIER]}(?:\\.${src[t.BUILDIDENTIFIER]})*))`);
    createToken("FULLPLAIN", `v?${src[t.MAINVERSION]}${src[t.PRERELEASE]}?${src[t.BUILD]}?`);
    createToken("FULL", `^${src[t.FULLPLAIN]}$`);
    createToken("LOOSEPLAIN", `[v=\\s]*${src[t.MAINVERSIONLOOSE]}${src[t.PRERELEASELOOSE]}?${src[t.BUILD]}?`);
    createToken("LOOSE", `^${src[t.LOOSEPLAIN]}$`);
    createToken("GTLT", "((?:<|>)?=?)");
    createToken("XRANGEIDENTIFIERLOOSE", `${src[t.NUMERICIDENTIFIERLOOSE]}|x|X|\\*`);
    createToken("XRANGEIDENTIFIER", `${src[t.NUMERICIDENTIFIER]}|x|X|\\*`);
    createToken("XRANGEPLAIN", `[v=\\s]*(${src[t.XRANGEIDENTIFIER]})(?:\\.(${src[t.XRANGEIDENTIFIER]})(?:\\.(${src[t.XRANGEIDENTIFIER]})(?:${src[t.PRERELEASE]})?${src[t.BUILD]}?)?)?`);
    createToken("XRANGEPLAINLOOSE", `[v=\\s]*(${src[t.XRANGEIDENTIFIERLOOSE]})(?:\\.(${src[t.XRANGEIDENTIFIERLOOSE]})(?:\\.(${src[t.XRANGEIDENTIFIERLOOSE]})(?:${src[t.PRERELEASELOOSE]})?${src[t.BUILD]}?)?)?`);
    createToken("XRANGE", `^${src[t.GTLT]}\\s*${src[t.XRANGEPLAIN]}$`);
    createToken("XRANGELOOSE", `^${src[t.GTLT]}\\s*${src[t.XRANGEPLAINLOOSE]}$`);
    createToken("COERCEPLAIN", `${"(^|[^\\d])(\\d{1,"}${MAX_SAFE_COMPONENT_LENGTH}})(?:\\.(\\d{1,${MAX_SAFE_COMPONENT_LENGTH}}))?(?:\\.(\\d{1,${MAX_SAFE_COMPONENT_LENGTH}}))?`);
    createToken("COERCE", `${src[t.COERCEPLAIN]}(?:$|[^\\d])`);
    createToken("COERCEFULL", src[t.COERCEPLAIN] + `(?:${src[t.PRERELEASE]})?(?:${src[t.BUILD]})?(?:$|[^\\d])`);
    createToken("COERCERTL", src[t.COERCE], true);
    createToken("COERCERTLFULL", src[t.COERCEFULL], true);
    createToken("LONETILDE", "(?:~>?)");
    createToken("TILDETRIM", `(\\s*)${src[t.LONETILDE]}\\s+`, true);
    exports.tildeTrimReplace = "$1~";
    createToken("TILDE", `^${src[t.LONETILDE]}${src[t.XRANGEPLAIN]}$`);
    createToken("TILDELOOSE", `^${src[t.LONETILDE]}${src[t.XRANGEPLAINLOOSE]}$`);
    createToken("LONECARET", "(?:\\^)");
    createToken("CARETTRIM", `(\\s*)${src[t.LONECARET]}\\s+`, true);
    exports.caretTrimReplace = "$1^";
    createToken("CARET", `^${src[t.LONECARET]}${src[t.XRANGEPLAIN]}$`);
    createToken("CARETLOOSE", `^${src[t.LONECARET]}${src[t.XRANGEPLAINLOOSE]}$`);
    createToken("COMPARATORLOOSE", `^${src[t.GTLT]}\\s*(${src[t.LOOSEPLAIN]})$|^$`);
    createToken("COMPARATOR", `^${src[t.GTLT]}\\s*(${src[t.FULLPLAIN]})$|^$`);
    createToken("COMPARATORTRIM", `(\\s*)${src[t.GTLT]}\\s*(${src[t.LOOSEPLAIN]}|${src[t.XRANGEPLAIN]})`, true);
    exports.comparatorTrimReplace = "$1$2$3";
    createToken("HYPHENRANGE", `^\\s*(${src[t.XRANGEPLAIN]})\\s+-\\s+(${src[t.XRANGEPLAIN]})\\s*$`);
    createToken("HYPHENRANGELOOSE", `^\\s*(${src[t.XRANGEPLAINLOOSE]})\\s+-\\s+(${src[t.XRANGEPLAINLOOSE]})\\s*$`);
    createToken("STAR", "(<|>)?=?\\s*\\*");
    createToken("GTE0", "^\\s*>=\\s*0\\.0\\.0\\s*$");
    createToken("GTE0PRE", "^\\s*>=\\s*0\\.0\\.0-0\\s*$");
  }
});

// node_modules/semver/internal/parse-options.js
var require_parse_options = __commonJS({
  "node_modules/semver/internal/parse-options.js"(exports, module) {
    "use strict";
    var looseOption = Object.freeze({ loose: true });
    var emptyOpts = Object.freeze({});
    var parseOptions = (options) => {
      if (!options) {
        return emptyOpts;
      }
      if (typeof options !== "object") {
        return looseOption;
      }
      return options;
    };
    module.exports = parseOptions;
  }
});

// node_modules/semver/internal/identifiers.js
var require_identifiers = __commonJS({
  "node_modules/semver/internal/identifiers.js"(exports, module) {
    "use strict";
    var numeric = /^[0-9]+$/;
    var compareIdentifiers = (a, b) => {
      if (typeof a === "number" && typeof b === "number") {
        return a === b ? 0 : a < b ? -1 : 1;
      }
      const anum = numeric.test(a);
      const bnum = numeric.test(b);
      if (anum && bnum) {
        a = +a;
        b = +b;
      }
      return a === b ? 0 : anum && !bnum ? -1 : bnum && !anum ? 1 : a < b ? -1 : 1;
    };
    var rcompareIdentifiers = (a, b) => compareIdentifiers(b, a);
    module.exports = {
      compareIdentifiers,
      rcompareIdentifiers
    };
  }
});

// node_modules/semver/classes/semver.js
var require_semver = __commonJS({
  "node_modules/semver/classes/semver.js"(exports, module) {
    "use strict";
    var debug = require_debug();
    var { MAX_LENGTH, MAX_SAFE_INTEGER } = require_constants();
    var { safeRe: re, t } = require_re();
    var parseOptions = require_parse_options();
    var { compareIdentifiers } = require_identifiers();
    var isPrereleaseIdentifier = (prerelease, identifier) => {
      const identifiers = identifier.split(".");
      if (identifiers.length > prerelease.length) {
        return false;
      }
      for (let i = 0; i < identifiers.length; i++) {
        if (compareIdentifiers(prerelease[i], identifiers[i]) !== 0) {
          return false;
        }
      }
      return true;
    };
    var SemVer = class _SemVer {
      constructor(version, options) {
        options = parseOptions(options);
        if (version instanceof _SemVer) {
          if (version.loose === !!options.loose && version.includePrerelease === !!options.includePrerelease) {
            return version;
          } else {
            version = version.version;
          }
        } else if (typeof version !== "string") {
          throw new TypeError(`Invalid version. Must be a string. Got type "${typeof version}".`);
        }
        if (version.length > MAX_LENGTH) {
          throw new TypeError(
            `version is longer than ${MAX_LENGTH} characters`
          );
        }
        debug("SemVer", version, options);
        this.options = options;
        this.loose = !!options.loose;
        this.includePrerelease = !!options.includePrerelease;
        const m = version.trim().match(options.loose ? re[t.LOOSE] : re[t.FULL]);
        if (!m) {
          throw new TypeError(`Invalid Version: ${version}`);
        }
        this.raw = version;
        this.major = +m[1];
        this.minor = +m[2];
        this.patch = +m[3];
        if (this.major > MAX_SAFE_INTEGER || this.major < 0) {
          throw new TypeError("Invalid major version");
        }
        if (this.minor > MAX_SAFE_INTEGER || this.minor < 0) {
          throw new TypeError("Invalid minor version");
        }
        if (this.patch > MAX_SAFE_INTEGER || this.patch < 0) {
          throw new TypeError("Invalid patch version");
        }
        if (!m[4]) {
          this.prerelease = [];
        } else {
          this.prerelease = m[4].split(".").map((id) => {
            if (/^[0-9]+$/.test(id)) {
              const num = +id;
              if (num >= 0 && num < MAX_SAFE_INTEGER) {
                return num;
              }
            }
            return id;
          });
        }
        this.build = m[5] ? m[5].split(".") : [];
        this.format();
      }
      format() {
        this.version = `${this.major}.${this.minor}.${this.patch}`;
        if (this.prerelease.length) {
          this.version += `-${this.prerelease.join(".")}`;
        }
        return this.version;
      }
      toString() {
        return this.version;
      }
      compare(other) {
        debug("SemVer.compare", this.version, this.options, other);
        if (!(other instanceof _SemVer)) {
          if (typeof other === "string" && other === this.version) {
            return 0;
          }
          other = new _SemVer(other, this.options);
        }
        if (other.version === this.version) {
          return 0;
        }
        return this.compareMain(other) || this.comparePre(other);
      }
      compareMain(other) {
        if (!(other instanceof _SemVer)) {
          other = new _SemVer(other, this.options);
        }
        if (this.major < other.major) {
          return -1;
        }
        if (this.major > other.major) {
          return 1;
        }
        if (this.minor < other.minor) {
          return -1;
        }
        if (this.minor > other.minor) {
          return 1;
        }
        if (this.patch < other.patch) {
          return -1;
        }
        if (this.patch > other.patch) {
          return 1;
        }
        return 0;
      }
      comparePre(other) {
        if (!(other instanceof _SemVer)) {
          other = new _SemVer(other, this.options);
        }
        if (this.prerelease.length && !other.prerelease.length) {
          return -1;
        } else if (!this.prerelease.length && other.prerelease.length) {
          return 1;
        } else if (!this.prerelease.length && !other.prerelease.length) {
          return 0;
        }
        let i = 0;
        do {
          const a = this.prerelease[i];
          const b = other.prerelease[i];
          debug("prerelease compare", i, a, b);
          if (a === void 0 && b === void 0) {
            return 0;
          } else if (b === void 0) {
            return 1;
          } else if (a === void 0) {
            return -1;
          } else if (a === b) {
            continue;
          } else {
            return compareIdentifiers(a, b);
          }
        } while (++i);
      }
      compareBuild(other) {
        if (!(other instanceof _SemVer)) {
          other = new _SemVer(other, this.options);
        }
        let i = 0;
        do {
          const a = this.build[i];
          const b = other.build[i];
          debug("build compare", i, a, b);
          if (a === void 0 && b === void 0) {
            return 0;
          } else if (b === void 0) {
            return 1;
          } else if (a === void 0) {
            return -1;
          } else if (a === b) {
            continue;
          } else {
            return compareIdentifiers(a, b);
          }
        } while (++i);
      }
      // preminor will bump the version up to the next minor release, and immediately
      // down to pre-release. premajor and prepatch work the same way.
      inc(release, identifier, identifierBase) {
        if (release.startsWith("pre")) {
          if (!identifier && identifierBase === false) {
            throw new Error("invalid increment argument: identifier is empty");
          }
          if (identifier) {
            const match = `-${identifier}`.match(this.options.loose ? re[t.PRERELEASELOOSE] : re[t.PRERELEASE]);
            if (!match || match[1] !== identifier) {
              throw new Error(`invalid identifier: ${identifier}`);
            }
          }
        }
        switch (release) {
          case "premajor":
            this.prerelease.length = 0;
            this.patch = 0;
            this.minor = 0;
            this.major++;
            this.inc("pre", identifier, identifierBase);
            break;
          case "preminor":
            this.prerelease.length = 0;
            this.patch = 0;
            this.minor++;
            this.inc("pre", identifier, identifierBase);
            break;
          case "prepatch":
            this.prerelease.length = 0;
            this.inc("patch", identifier, identifierBase);
            this.inc("pre", identifier, identifierBase);
            break;
          // If the input is a non-prerelease version, this acts the same as
          // prepatch.
          case "prerelease":
            if (this.prerelease.length === 0) {
              this.inc("patch", identifier, identifierBase);
            }
            this.inc("pre", identifier, identifierBase);
            break;
          case "release":
            if (this.prerelease.length === 0) {
              throw new Error(`version ${this.raw} is not a prerelease`);
            }
            this.prerelease.length = 0;
            break;
          case "major":
            if (this.minor !== 0 || this.patch !== 0 || this.prerelease.length === 0) {
              this.major++;
            }
            this.minor = 0;
            this.patch = 0;
            this.prerelease = [];
            break;
          case "minor":
            if (this.patch !== 0 || this.prerelease.length === 0) {
              this.minor++;
            }
            this.patch = 0;
            this.prerelease = [];
            break;
          case "patch":
            if (this.prerelease.length === 0) {
              this.patch++;
            }
            this.prerelease = [];
            break;
          // This probably shouldn't be used publicly.
          // 1.0.0 'pre' would become 1.0.0-0 which is the wrong direction.
          case "pre": {
            const base = Number(identifierBase) ? 1 : 0;
            if (this.prerelease.length === 0) {
              this.prerelease = [base];
            } else {
              let i = this.prerelease.length;
              while (--i >= 0) {
                if (typeof this.prerelease[i] === "number") {
                  this.prerelease[i]++;
                  i = -2;
                }
              }
              if (i === -1) {
                if (identifier === this.prerelease.join(".") && identifierBase === false) {
                  throw new Error("invalid increment argument: identifier already exists");
                }
                this.prerelease.push(base);
              }
            }
            if (identifier) {
              let prerelease = [identifier, base];
              if (identifierBase === false) {
                prerelease = [identifier];
              }
              if (isPrereleaseIdentifier(this.prerelease, identifier)) {
                const prereleaseBase = this.prerelease[identifier.split(".").length];
                if (isNaN(prereleaseBase)) {
                  this.prerelease = prerelease;
                }
              } else {
                this.prerelease = prerelease;
              }
            }
            break;
          }
          default:
            throw new Error(`invalid increment argument: ${release}`);
        }
        this.raw = this.format();
        if (this.build.length) {
          this.raw += `+${this.build.join(".")}`;
        }
        return this;
      }
    };
    module.exports = SemVer;
  }
});

// node_modules/semver/functions/parse.js
var require_parse = __commonJS({
  "node_modules/semver/functions/parse.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var parse = (version, options, throwErrors = false) => {
      if (version instanceof SemVer) {
        return version;
      }
      try {
        return new SemVer(version, options);
      } catch (er) {
        if (!throwErrors) {
          return null;
        }
        throw er;
      }
    };
    module.exports = parse;
  }
});

// node_modules/semver/functions/valid.js
var require_valid = __commonJS({
  "node_modules/semver/functions/valid.js"(exports, module) {
    "use strict";
    var parse = require_parse();
    var valid = (version, options) => {
      const v = parse(version, options);
      return v ? v.version : null;
    };
    module.exports = valid;
  }
});

// node_modules/semver/functions/clean.js
var require_clean = __commonJS({
  "node_modules/semver/functions/clean.js"(exports, module) {
    "use strict";
    var parse = require_parse();
    var clean = (version, options) => {
      const s = parse(version.trim().replace(/^[=v]+/, ""), options);
      return s ? s.version : null;
    };
    module.exports = clean;
  }
});

// node_modules/semver/functions/inc.js
var require_inc = __commonJS({
  "node_modules/semver/functions/inc.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var inc = (version, release, options, identifier, identifierBase) => {
      if (typeof options === "string") {
        identifierBase = identifier;
        identifier = options;
        options = void 0;
      }
      try {
        return new SemVer(
          version instanceof SemVer ? version.version : version,
          options
        ).inc(release, identifier, identifierBase).version;
      } catch (er) {
        return null;
      }
    };
    module.exports = inc;
  }
});

// node_modules/semver/functions/diff.js
var require_diff = __commonJS({
  "node_modules/semver/functions/diff.js"(exports, module) {
    "use strict";
    var parse = require_parse();
    var diff = (version1, version2) => {
      const v1 = parse(version1, null, true);
      const v2 = parse(version2, null, true);
      const comparison = v1.compare(v2);
      if (comparison === 0) {
        return null;
      }
      const v1Higher = comparison > 0;
      const highVersion = v1Higher ? v1 : v2;
      const lowVersion = v1Higher ? v2 : v1;
      const highHasPre = !!highVersion.prerelease.length;
      const lowHasPre = !!lowVersion.prerelease.length;
      if (lowHasPre && !highHasPre) {
        if (!lowVersion.patch && !lowVersion.minor) {
          return "major";
        }
        if (lowVersion.compareMain(highVersion) === 0) {
          if (lowVersion.minor && !lowVersion.patch) {
            return "minor";
          }
          return "patch";
        }
      }
      const prefix = highHasPre ? "pre" : "";
      if (v1.major !== v2.major) {
        return prefix + "major";
      }
      if (v1.minor !== v2.minor) {
        return prefix + "minor";
      }
      if (v1.patch !== v2.patch) {
        return prefix + "patch";
      }
      return "prerelease";
    };
    module.exports = diff;
  }
});

// node_modules/semver/functions/major.js
var require_major = __commonJS({
  "node_modules/semver/functions/major.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var major = (a, loose) => new SemVer(a, loose).major;
    module.exports = major;
  }
});

// node_modules/semver/functions/minor.js
var require_minor = __commonJS({
  "node_modules/semver/functions/minor.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var minor = (a, loose) => new SemVer(a, loose).minor;
    module.exports = minor;
  }
});

// node_modules/semver/functions/patch.js
var require_patch = __commonJS({
  "node_modules/semver/functions/patch.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var patch = (a, loose) => new SemVer(a, loose).patch;
    module.exports = patch;
  }
});

// node_modules/semver/functions/prerelease.js
var require_prerelease = __commonJS({
  "node_modules/semver/functions/prerelease.js"(exports, module) {
    "use strict";
    var parse = require_parse();
    var prerelease = (version, options) => {
      const parsed = parse(version, options);
      return parsed && parsed.prerelease.length ? parsed.prerelease : null;
    };
    module.exports = prerelease;
  }
});

// node_modules/semver/functions/compare.js
var require_compare = __commonJS({
  "node_modules/semver/functions/compare.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var compare2 = (a, b, loose) => new SemVer(a, loose).compare(new SemVer(b, loose));
    module.exports = compare2;
  }
});

// node_modules/semver/functions/rcompare.js
var require_rcompare = __commonJS({
  "node_modules/semver/functions/rcompare.js"(exports, module) {
    "use strict";
    var compare2 = require_compare();
    var rcompare = (a, b, loose) => compare2(b, a, loose);
    module.exports = rcompare;
  }
});

// node_modules/semver/functions/compare-loose.js
var require_compare_loose = __commonJS({
  "node_modules/semver/functions/compare-loose.js"(exports, module) {
    "use strict";
    var compare2 = require_compare();
    var compareLoose = (a, b) => compare2(a, b, true);
    module.exports = compareLoose;
  }
});

// node_modules/semver/functions/compare-build.js
var require_compare_build = __commonJS({
  "node_modules/semver/functions/compare-build.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var compareBuild = (a, b, loose) => {
      const versionA = new SemVer(a, loose);
      const versionB = new SemVer(b, loose);
      return versionA.compare(versionB) || versionA.compareBuild(versionB);
    };
    module.exports = compareBuild;
  }
});

// node_modules/semver/functions/sort.js
var require_sort = __commonJS({
  "node_modules/semver/functions/sort.js"(exports, module) {
    "use strict";
    var compareBuild = require_compare_build();
    var sort = (list, loose) => list.sort((a, b) => compareBuild(a, b, loose));
    module.exports = sort;
  }
});

// node_modules/semver/functions/rsort.js
var require_rsort = __commonJS({
  "node_modules/semver/functions/rsort.js"(exports, module) {
    "use strict";
    var compareBuild = require_compare_build();
    var rsort = (list, loose) => list.sort((a, b) => compareBuild(b, a, loose));
    module.exports = rsort;
  }
});

// node_modules/semver/functions/gt.js
var require_gt = __commonJS({
  "node_modules/semver/functions/gt.js"(exports, module) {
    "use strict";
    var compare2 = require_compare();
    var gt = (a, b, loose) => compare2(a, b, loose) > 0;
    module.exports = gt;
  }
});

// node_modules/semver/functions/lt.js
var require_lt = __commonJS({
  "node_modules/semver/functions/lt.js"(exports, module) {
    "use strict";
    var compare2 = require_compare();
    var lt = (a, b, loose) => compare2(a, b, loose) < 0;
    module.exports = lt;
  }
});

// node_modules/semver/functions/eq.js
var require_eq = __commonJS({
  "node_modules/semver/functions/eq.js"(exports, module) {
    "use strict";
    var compare2 = require_compare();
    var eq = (a, b, loose) => compare2(a, b, loose) === 0;
    module.exports = eq;
  }
});

// node_modules/semver/functions/neq.js
var require_neq = __commonJS({
  "node_modules/semver/functions/neq.js"(exports, module) {
    "use strict";
    var compare2 = require_compare();
    var neq = (a, b, loose) => compare2(a, b, loose) !== 0;
    module.exports = neq;
  }
});

// node_modules/semver/functions/gte.js
var require_gte = __commonJS({
  "node_modules/semver/functions/gte.js"(exports, module) {
    "use strict";
    var compare2 = require_compare();
    var gte = (a, b, loose) => compare2(a, b, loose) >= 0;
    module.exports = gte;
  }
});

// node_modules/semver/functions/lte.js
var require_lte = __commonJS({
  "node_modules/semver/functions/lte.js"(exports, module) {
    "use strict";
    var compare2 = require_compare();
    var lte = (a, b, loose) => compare2(a, b, loose) <= 0;
    module.exports = lte;
  }
});

// node_modules/semver/functions/cmp.js
var require_cmp = __commonJS({
  "node_modules/semver/functions/cmp.js"(exports, module) {
    "use strict";
    var eq = require_eq();
    var neq = require_neq();
    var gt = require_gt();
    var gte = require_gte();
    var lt = require_lt();
    var lte = require_lte();
    var cmp = (a, op, b, loose) => {
      switch (op) {
        case "===":
          if (typeof a === "object") {
            a = a.version;
          }
          if (typeof b === "object") {
            b = b.version;
          }
          return a === b;
        case "!==":
          if (typeof a === "object") {
            a = a.version;
          }
          if (typeof b === "object") {
            b = b.version;
          }
          return a !== b;
        case "":
        case "=":
        case "==":
          return eq(a, b, loose);
        case "!=":
          return neq(a, b, loose);
        case ">":
          return gt(a, b, loose);
        case ">=":
          return gte(a, b, loose);
        case "<":
          return lt(a, b, loose);
        case "<=":
          return lte(a, b, loose);
        default:
          throw new TypeError(`Invalid operator: ${op}`);
      }
    };
    module.exports = cmp;
  }
});

// node_modules/semver/functions/coerce.js
var require_coerce = __commonJS({
  "node_modules/semver/functions/coerce.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var parse = require_parse();
    var { safeRe: re, t } = require_re();
    var coerce = (version, options) => {
      if (version instanceof SemVer) {
        return version;
      }
      if (typeof version === "number") {
        version = String(version);
      }
      if (typeof version !== "string") {
        return null;
      }
      options = options || {};
      let match = null;
      if (!options.rtl) {
        match = version.match(options.includePrerelease ? re[t.COERCEFULL] : re[t.COERCE]);
      } else {
        const coerceRtlRegex = options.includePrerelease ? re[t.COERCERTLFULL] : re[t.COERCERTL];
        let next;
        while ((next = coerceRtlRegex.exec(version)) && (!match || match.index + match[0].length !== version.length)) {
          if (!match || next.index + next[0].length !== match.index + match[0].length) {
            match = next;
          }
          coerceRtlRegex.lastIndex = next.index + next[1].length + next[2].length;
        }
        coerceRtlRegex.lastIndex = -1;
      }
      if (match === null) {
        return null;
      }
      const major = match[2];
      const minor = match[3] || "0";
      const patch = match[4] || "0";
      const prerelease = options.includePrerelease && match[5] ? `-${match[5]}` : "";
      const build = options.includePrerelease && match[6] ? `+${match[6]}` : "";
      return parse(`${major}.${minor}.${patch}${prerelease}${build}`, options);
    };
    module.exports = coerce;
  }
});

// node_modules/semver/functions/truncate.js
var require_truncate = __commonJS({
  "node_modules/semver/functions/truncate.js"(exports, module) {
    "use strict";
    var parse = require_parse();
    var constants4 = require_constants();
    var SemVer = require_semver();
    var truncate = (version, truncation, options) => {
      if (!constants4.RELEASE_TYPES.includes(truncation)) {
        return null;
      }
      const clonedVersion = cloneInputVersion(version, options);
      return clonedVersion && doTruncation(clonedVersion, truncation);
    };
    var cloneInputVersion = (version, options) => {
      const versionStringToParse = version instanceof SemVer ? version.version : version;
      return parse(versionStringToParse, options);
    };
    var doTruncation = (version, truncation) => {
      if (isPrerelease(truncation)) {
        return version.version;
      }
      version.prerelease = [];
      switch (truncation) {
        case "major":
          version.minor = 0;
          version.patch = 0;
          break;
        case "minor":
          version.patch = 0;
          break;
      }
      return version.format();
    };
    var isPrerelease = (type) => {
      return type.startsWith("pre");
    };
    module.exports = truncate;
  }
});

// node_modules/semver/internal/lrucache.js
var require_lrucache = __commonJS({
  "node_modules/semver/internal/lrucache.js"(exports, module) {
    "use strict";
    var LRUCache = class {
      constructor() {
        this.max = 1e3;
        this.map = /* @__PURE__ */ new Map();
      }
      get(key) {
        const value = this.map.get(key);
        if (value === void 0) {
          return void 0;
        } else {
          this.map.delete(key);
          this.map.set(key, value);
          return value;
        }
      }
      delete(key) {
        return this.map.delete(key);
      }
      set(key, value) {
        const deleted = this.delete(key);
        if (!deleted && value !== void 0) {
          if (this.map.size >= this.max) {
            const firstKey = this.map.keys().next().value;
            this.delete(firstKey);
          }
          this.map.set(key, value);
        }
        return this;
      }
    };
    module.exports = LRUCache;
  }
});

// node_modules/semver/classes/range.js
var require_range = __commonJS({
  "node_modules/semver/classes/range.js"(exports, module) {
    "use strict";
    var SPACE_CHARACTERS = /\s+/g;
    var Range = class _Range {
      constructor(range, options) {
        options = parseOptions(options);
        if (range instanceof _Range) {
          if (range.loose === !!options.loose && range.includePrerelease === !!options.includePrerelease) {
            return range;
          } else {
            return new _Range(range.raw, options);
          }
        }
        if (range instanceof Comparator) {
          this.raw = range.value;
          this.set = [[range]];
          this.formatted = void 0;
          return this;
        }
        this.options = options;
        this.loose = !!options.loose;
        this.includePrerelease = !!options.includePrerelease;
        this.raw = range.trim().replace(SPACE_CHARACTERS, " ");
        this.set = this.raw.split("||").map((r) => this.parseRange(r.trim())).filter((c) => c.length);
        if (!this.set.length) {
          throw new TypeError(`Invalid SemVer Range: ${this.raw}`);
        }
        if (this.set.length > 1) {
          const first = this.set[0];
          this.set = this.set.filter((c) => !isNullSet(c[0]));
          if (this.set.length === 0) {
            this.set = [first];
          } else if (this.set.length > 1) {
            for (const c of this.set) {
              if (c.length === 1 && isAny(c[0])) {
                this.set = [c];
                break;
              }
            }
          }
        }
        this.formatted = void 0;
      }
      get range() {
        if (this.formatted === void 0) {
          this.formatted = "";
          for (let i = 0; i < this.set.length; i++) {
            if (i > 0) {
              this.formatted += "||";
            }
            const comps = this.set[i];
            for (let k = 0; k < comps.length; k++) {
              if (k > 0) {
                this.formatted += " ";
              }
              this.formatted += comps[k].toString().trim();
            }
          }
        }
        return this.formatted;
      }
      format() {
        return this.range;
      }
      toString() {
        return this.range;
      }
      parseRange(range) {
        range = range.replace(BUILDSTRIPRE, "");
        const memoOpts = (this.options.includePrerelease && FLAG_INCLUDE_PRERELEASE) | (this.options.loose && FLAG_LOOSE);
        const memoKey = memoOpts + ":" + range;
        const cached = cache.get(memoKey);
        if (cached) {
          return cached;
        }
        const loose = this.options.loose;
        const hr = loose ? re[t.HYPHENRANGELOOSE] : re[t.HYPHENRANGE];
        range = range.replace(hr, hyphenReplace(this.options.includePrerelease));
        debug("hyphen replace", range);
        range = range.replace(re[t.COMPARATORTRIM], comparatorTrimReplace);
        debug("comparator trim", range);
        range = range.replace(re[t.TILDETRIM], tildeTrimReplace);
        debug("tilde trim", range);
        range = range.replace(re[t.CARETTRIM], caretTrimReplace);
        debug("caret trim", range);
        let rangeList = range.split(" ").map((comp) => parseComparator(comp, this.options)).join(" ").split(/\s+/).map((comp) => replaceGTE0(comp, this.options));
        if (loose) {
          rangeList = rangeList.filter((comp) => {
            debug("loose invalid filter", comp, this.options);
            return !!comp.match(re[t.COMPARATORLOOSE]);
          });
        }
        debug("range list", rangeList);
        const rangeMap = /* @__PURE__ */ new Map();
        const comparators = rangeList.map((comp) => new Comparator(comp, this.options));
        for (const comp of comparators) {
          if (isNullSet(comp)) {
            return [comp];
          }
          rangeMap.set(comp.value, comp);
        }
        if (rangeMap.size > 1 && rangeMap.has("")) {
          rangeMap.delete("");
        }
        const result = [...rangeMap.values()];
        cache.set(memoKey, result);
        return result;
      }
      intersects(range, options) {
        if (!(range instanceof _Range)) {
          throw new TypeError("a Range is required");
        }
        return this.set.some((thisComparators) => {
          return isSatisfiable(thisComparators, options) && range.set.some((rangeComparators) => {
            return isSatisfiable(rangeComparators, options) && thisComparators.every((thisComparator) => {
              return rangeComparators.every((rangeComparator) => {
                return thisComparator.intersects(rangeComparator, options);
              });
            });
          });
        });
      }
      // if ANY of the sets match ALL of its comparators, then pass
      test(version) {
        if (!version) {
          return false;
        }
        if (typeof version === "string") {
          try {
            version = new SemVer(version, this.options);
          } catch (er) {
            return false;
          }
        }
        for (let i = 0; i < this.set.length; i++) {
          if (testSet(this.set[i], version, this.options)) {
            return true;
          }
        }
        return false;
      }
    };
    module.exports = Range;
    var LRU = require_lrucache();
    var cache = new LRU();
    var parseOptions = require_parse_options();
    var Comparator = require_comparator();
    var debug = require_debug();
    var SemVer = require_semver();
    var {
      safeRe: re,
      src,
      t,
      comparatorTrimReplace,
      tildeTrimReplace,
      caretTrimReplace
    } = require_re();
    var { FLAG_INCLUDE_PRERELEASE, FLAG_LOOSE } = require_constants();
    var BUILDSTRIPRE = new RegExp(src[t.BUILD], "g");
    var isNullSet = (c) => c.value === "<0.0.0-0";
    var isAny = (c) => c.value === "";
    var isSatisfiable = (comparators, options) => {
      let result = true;
      const remainingComparators = comparators.slice();
      let testComparator = remainingComparators.pop();
      while (result && remainingComparators.length) {
        result = remainingComparators.every((otherComparator) => {
          return testComparator.intersects(otherComparator, options);
        });
        testComparator = remainingComparators.pop();
      }
      return result;
    };
    var parseComparator = (comp, options) => {
      comp = comp.replace(re[t.BUILD], "");
      debug("comp", comp, options);
      comp = replaceCarets(comp, options);
      debug("caret", comp);
      comp = replaceTildes(comp, options);
      debug("tildes", comp);
      comp = replaceXRanges(comp, options);
      debug("xrange", comp);
      comp = replaceStars(comp, options);
      debug("stars", comp);
      return comp;
    };
    var isX = (id) => !id || id.toLowerCase() === "x" || id === "*";
    var invalidXRangeOrder = (M, m, p) => isX(M) && !isX(m) || isX(m) && p && !isX(p);
    var replaceTildes = (comp, options) => {
      return comp.trim().split(/\s+/).map((c) => replaceTilde(c, options)).join(" ");
    };
    var replaceTilde = (comp, options) => {
      const r = options.loose ? re[t.TILDELOOSE] : re[t.TILDE];
      const z = options.includePrerelease ? "-0" : "";
      return comp.replace(r, (_, M, m, p, pr) => {
        debug("tilde", comp, _, M, m, p, pr);
        let ret;
        if (isX(M)) {
          ret = "";
        } else if (isX(m)) {
          ret = `>=${M}.0.0${z} <${+M + 1}.0.0-0`;
        } else if (isX(p)) {
          ret = `>=${M}.${m}.0${z} <${M}.${+m + 1}.0-0`;
        } else if (pr) {
          debug("replaceTilde pr", pr);
          ret = `>=${M}.${m}.${p}-${pr} <${M}.${+m + 1}.0-0`;
        } else {
          ret = `>=${M}.${m}.${p} <${M}.${+m + 1}.0-0`;
        }
        debug("tilde return", ret);
        return ret;
      });
    };
    var replaceCarets = (comp, options) => {
      return comp.trim().split(/\s+/).map((c) => replaceCaret(c, options)).join(" ");
    };
    var replaceCaret = (comp, options) => {
      debug("caret", comp, options);
      const r = options.loose ? re[t.CARETLOOSE] : re[t.CARET];
      const z = options.includePrerelease ? "-0" : "";
      return comp.replace(r, (_, M, m, p, pr) => {
        debug("caret", comp, _, M, m, p, pr);
        let ret;
        if (isX(M)) {
          ret = "";
        } else if (isX(m)) {
          ret = `>=${M}.0.0${z} <${+M + 1}.0.0-0`;
        } else if (isX(p)) {
          if (M === "0") {
            ret = `>=${M}.${m}.0${z} <${M}.${+m + 1}.0-0`;
          } else {
            ret = `>=${M}.${m}.0${z} <${+M + 1}.0.0-0`;
          }
        } else if (pr) {
          debug("replaceCaret pr", pr);
          if (M === "0") {
            if (m === "0") {
              ret = `>=${M}.${m}.${p}-${pr} <${M}.${m}.${+p + 1}-0`;
            } else {
              ret = `>=${M}.${m}.${p}-${pr} <${M}.${+m + 1}.0-0`;
            }
          } else {
            ret = `>=${M}.${m}.${p}-${pr} <${+M + 1}.0.0-0`;
          }
        } else {
          debug("no pr");
          if (M === "0") {
            if (m === "0") {
              ret = `>=${M}.${m}.${p} <${M}.${m}.${+p + 1}-0`;
            } else {
              ret = `>=${M}.${m}.${p} <${M}.${+m + 1}.0-0`;
            }
          } else {
            ret = `>=${M}.${m}.${p} <${+M + 1}.0.0-0`;
          }
        }
        debug("caret return", ret);
        return ret;
      });
    };
    var replaceXRanges = (comp, options) => {
      debug("replaceXRanges", comp, options);
      return comp.split(/\s+/).map((c) => replaceXRange(c, options)).join(" ");
    };
    var replaceXRange = (comp, options) => {
      comp = comp.trim();
      const r = options.loose ? re[t.XRANGELOOSE] : re[t.XRANGE];
      return comp.replace(r, (ret, gtlt, M, m, p, pr) => {
        debug("xRange", comp, ret, gtlt, M, m, p, pr);
        if (invalidXRangeOrder(M, m, p)) {
          return comp;
        }
        const xM = isX(M);
        const xm = xM || isX(m);
        const xp = xm || isX(p);
        const anyX = xp;
        if (gtlt === "=" && anyX) {
          gtlt = "";
        }
        pr = options.includePrerelease ? "-0" : "";
        if (xM) {
          if (gtlt === ">" || gtlt === "<") {
            ret = "<0.0.0-0";
          } else {
            ret = "*";
          }
        } else if (gtlt && anyX) {
          if (xm) {
            m = 0;
          }
          p = 0;
          if (gtlt === ">") {
            gtlt = ">=";
            if (xm) {
              M = +M + 1;
              m = 0;
              p = 0;
            } else {
              m = +m + 1;
              p = 0;
            }
          } else if (gtlt === "<=") {
            gtlt = "<";
            if (xm) {
              M = +M + 1;
            } else {
              m = +m + 1;
            }
          }
          if (gtlt === "<") {
            pr = "-0";
          }
          ret = `${gtlt + M}.${m}.${p}${pr}`;
        } else if (xm) {
          ret = `>=${M}.0.0${pr} <${+M + 1}.0.0-0`;
        } else if (xp) {
          ret = `>=${M}.${m}.0${pr} <${M}.${+m + 1}.0-0`;
        }
        debug("xRange return", ret);
        return ret;
      });
    };
    var replaceStars = (comp, options) => {
      debug("replaceStars", comp, options);
      return comp.trim().replace(re[t.STAR], "");
    };
    var replaceGTE0 = (comp, options) => {
      debug("replaceGTE0", comp, options);
      return comp.trim().replace(re[options.includePrerelease ? t.GTE0PRE : t.GTE0], "");
    };
    var hyphenReplace = (incPr) => ($0, from, fM, fm, fp, fpr, fb, to, tM, tm, tp, tpr) => {
      if (isX(fM)) {
        from = "";
      } else if (isX(fm)) {
        from = `>=${fM}.0.0${incPr ? "-0" : ""}`;
      } else if (isX(fp)) {
        from = `>=${fM}.${fm}.0${incPr ? "-0" : ""}`;
      } else if (fpr) {
        from = `>=${from}`;
      } else {
        from = `>=${from}${incPr ? "-0" : ""}`;
      }
      if (isX(tM)) {
        to = "";
      } else if (isX(tm)) {
        to = `<${+tM + 1}.0.0-0`;
      } else if (isX(tp)) {
        to = `<${tM}.${+tm + 1}.0-0`;
      } else if (tpr) {
        to = `<=${tM}.${tm}.${tp}-${tpr}`;
      } else if (incPr) {
        to = `<${tM}.${tm}.${+tp + 1}-0`;
      } else {
        to = `<=${to}`;
      }
      return `${from} ${to}`.trim();
    };
    var testSet = (set, version, options) => {
      for (let i = 0; i < set.length; i++) {
        if (!set[i].test(version)) {
          return false;
        }
      }
      if (version.prerelease.length && !options.includePrerelease) {
        for (let i = 0; i < set.length; i++) {
          debug(set[i].semver);
          if (set[i].semver === Comparator.ANY) {
            continue;
          }
          if (set[i].semver.prerelease.length > 0) {
            const allowed = set[i].semver;
            if (allowed.major === version.major && allowed.minor === version.minor && allowed.patch === version.patch) {
              return true;
            }
          }
        }
        return false;
      }
      return true;
    };
  }
});

// node_modules/semver/classes/comparator.js
var require_comparator = __commonJS({
  "node_modules/semver/classes/comparator.js"(exports, module) {
    "use strict";
    var ANY = /* @__PURE__ */ Symbol("SemVer ANY");
    var Comparator = class _Comparator {
      static get ANY() {
        return ANY;
      }
      constructor(comp, options) {
        options = parseOptions(options);
        if (comp instanceof _Comparator) {
          if (comp.loose === !!options.loose) {
            return comp;
          } else {
            comp = comp.value;
          }
        }
        comp = comp.trim().split(/\s+/).join(" ");
        debug("comparator", comp, options);
        this.options = options;
        this.loose = !!options.loose;
        this.parse(comp);
        if (this.semver === ANY) {
          this.value = "";
        } else {
          this.value = this.operator + this.semver.version;
        }
        debug("comp", this);
      }
      parse(comp) {
        const r = this.options.loose ? re[t.COMPARATORLOOSE] : re[t.COMPARATOR];
        const m = comp.match(r);
        if (!m) {
          throw new TypeError(`Invalid comparator: ${comp}`);
        }
        this.operator = m[1] !== void 0 ? m[1] : "";
        if (this.operator === "=") {
          this.operator = "";
        }
        if (!m[2]) {
          this.semver = ANY;
        } else {
          this.semver = new SemVer(m[2], this.options.loose);
        }
      }
      toString() {
        return this.value;
      }
      test(version) {
        debug("Comparator.test", version, this.options.loose);
        if (this.semver === ANY || version === ANY) {
          return true;
        }
        if (typeof version === "string") {
          try {
            version = new SemVer(version, this.options);
          } catch (er) {
            return false;
          }
        }
        return cmp(version, this.operator, this.semver, this.options);
      }
      intersects(comp, options) {
        if (!(comp instanceof _Comparator)) {
          throw new TypeError("a Comparator is required");
        }
        if (this.operator === "") {
          if (this.value === "") {
            return true;
          }
          return new Range(comp.value, options).test(this.value);
        } else if (comp.operator === "") {
          if (comp.value === "") {
            return true;
          }
          return new Range(this.value, options).test(comp.semver);
        }
        options = parseOptions(options);
        if (options.includePrerelease && (this.value === "<0.0.0-0" || comp.value === "<0.0.0-0")) {
          return false;
        }
        if (!options.includePrerelease && (this.value.startsWith("<0.0.0") || comp.value.startsWith("<0.0.0"))) {
          return false;
        }
        if (this.operator.startsWith(">") && comp.operator.startsWith(">")) {
          return true;
        }
        if (this.operator.startsWith("<") && comp.operator.startsWith("<")) {
          return true;
        }
        if (this.semver.version === comp.semver.version && this.operator.includes("=") && comp.operator.includes("=")) {
          return true;
        }
        if (cmp(this.semver, "<", comp.semver, options) && this.operator.startsWith(">") && comp.operator.startsWith("<")) {
          return true;
        }
        if (cmp(this.semver, ">", comp.semver, options) && this.operator.startsWith("<") && comp.operator.startsWith(">")) {
          return true;
        }
        return false;
      }
    };
    module.exports = Comparator;
    var parseOptions = require_parse_options();
    var { safeRe: re, t } = require_re();
    var cmp = require_cmp();
    var debug = require_debug();
    var SemVer = require_semver();
    var Range = require_range();
  }
});

// node_modules/semver/functions/satisfies.js
var require_satisfies = __commonJS({
  "node_modules/semver/functions/satisfies.js"(exports, module) {
    "use strict";
    var Range = require_range();
    var satisfies = (version, range, options) => {
      try {
        range = new Range(range, options);
      } catch (er) {
        return false;
      }
      return range.test(version);
    };
    module.exports = satisfies;
  }
});

// node_modules/semver/ranges/to-comparators.js
var require_to_comparators = __commonJS({
  "node_modules/semver/ranges/to-comparators.js"(exports, module) {
    "use strict";
    var Range = require_range();
    var toComparators = (range, options) => new Range(range, options).set.map((comp) => comp.map((c) => c.value).join(" ").trim().split(" "));
    module.exports = toComparators;
  }
});

// node_modules/semver/ranges/max-satisfying.js
var require_max_satisfying = __commonJS({
  "node_modules/semver/ranges/max-satisfying.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var Range = require_range();
    var maxSatisfying = (versions, range, options) => {
      let max = null;
      let maxSV = null;
      let rangeObj = null;
      try {
        rangeObj = new Range(range, options);
      } catch (er) {
        return null;
      }
      versions.forEach((v) => {
        if (rangeObj.test(v)) {
          if (!max || maxSV.compare(v) === -1) {
            max = v;
            maxSV = new SemVer(max, options);
          }
        }
      });
      return max;
    };
    module.exports = maxSatisfying;
  }
});

// node_modules/semver/ranges/min-satisfying.js
var require_min_satisfying = __commonJS({
  "node_modules/semver/ranges/min-satisfying.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var Range = require_range();
    var minSatisfying = (versions, range, options) => {
      let min = null;
      let minSV = null;
      let rangeObj = null;
      try {
        rangeObj = new Range(range, options);
      } catch (er) {
        return null;
      }
      versions.forEach((v) => {
        if (rangeObj.test(v)) {
          if (!min || minSV.compare(v) === 1) {
            min = v;
            minSV = new SemVer(min, options);
          }
        }
      });
      return min;
    };
    module.exports = minSatisfying;
  }
});

// node_modules/semver/ranges/min-version.js
var require_min_version = __commonJS({
  "node_modules/semver/ranges/min-version.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var Range = require_range();
    var gt = require_gt();
    var minVersion = (range, loose) => {
      range = new Range(range, loose);
      let minver = new SemVer("0.0.0");
      if (range.test(minver)) {
        return minver;
      }
      minver = new SemVer("0.0.0-0");
      if (range.test(minver)) {
        return minver;
      }
      minver = null;
      for (let i = 0; i < range.set.length; ++i) {
        const comparators = range.set[i];
        let setMin = null;
        comparators.forEach((comparator) => {
          const compver = new SemVer(comparator.semver.version);
          switch (comparator.operator) {
            case ">":
              if (compver.prerelease.length === 0) {
                compver.patch++;
              } else {
                compver.prerelease.push(0);
              }
              compver.raw = compver.format();
            /* fallthrough */
            case "":
            case ">=":
              if (!setMin || gt(compver, setMin)) {
                setMin = compver;
              }
              break;
            case "<":
            case "<=":
              break;
            /* istanbul ignore next */
            default:
              throw new Error(`Unexpected operation: ${comparator.operator}`);
          }
        });
        if (setMin && (!minver || gt(minver, setMin))) {
          minver = setMin;
        }
      }
      if (minver && range.test(minver)) {
        return minver;
      }
      return null;
    };
    module.exports = minVersion;
  }
});

// node_modules/semver/ranges/valid.js
var require_valid2 = __commonJS({
  "node_modules/semver/ranges/valid.js"(exports, module) {
    "use strict";
    var Range = require_range();
    var validRange = (range, options) => {
      try {
        return new Range(range, options).range || "*";
      } catch (er) {
        return null;
      }
    };
    module.exports = validRange;
  }
});

// node_modules/semver/ranges/outside.js
var require_outside = __commonJS({
  "node_modules/semver/ranges/outside.js"(exports, module) {
    "use strict";
    var SemVer = require_semver();
    var Comparator = require_comparator();
    var { ANY } = Comparator;
    var Range = require_range();
    var satisfies = require_satisfies();
    var gt = require_gt();
    var lt = require_lt();
    var lte = require_lte();
    var gte = require_gte();
    var outside = (version, range, hilo, options) => {
      version = new SemVer(version, options);
      range = new Range(range, options);
      let gtfn, ltefn, ltfn, comp, ecomp;
      switch (hilo) {
        case ">":
          gtfn = gt;
          ltefn = lte;
          ltfn = lt;
          comp = ">";
          ecomp = ">=";
          break;
        case "<":
          gtfn = lt;
          ltefn = gte;
          ltfn = gt;
          comp = "<";
          ecomp = "<=";
          break;
        default:
          throw new TypeError('Must provide a hilo val of "<" or ">"');
      }
      if (satisfies(version, range, options)) {
        return false;
      }
      for (let i = 0; i < range.set.length; ++i) {
        const comparators = range.set[i];
        let high = null;
        let low = null;
        comparators.forEach((comparator) => {
          if (comparator.semver === ANY) {
            comparator = new Comparator(">=0.0.0");
          }
          high = high || comparator;
          low = low || comparator;
          if (gtfn(comparator.semver, high.semver, options)) {
            high = comparator;
          } else if (ltfn(comparator.semver, low.semver, options)) {
            low = comparator;
          }
        });
        if (high.operator === comp || high.operator === ecomp) {
          return false;
        }
        if ((!low.operator || low.operator === comp) && ltefn(version, low.semver)) {
          return false;
        } else if (low.operator === ecomp && ltfn(version, low.semver)) {
          return false;
        }
      }
      return true;
    };
    module.exports = outside;
  }
});

// node_modules/semver/ranges/gtr.js
var require_gtr = __commonJS({
  "node_modules/semver/ranges/gtr.js"(exports, module) {
    "use strict";
    var outside = require_outside();
    var gtr = (version, range, options) => outside(version, range, ">", options);
    module.exports = gtr;
  }
});

// node_modules/semver/ranges/ltr.js
var require_ltr = __commonJS({
  "node_modules/semver/ranges/ltr.js"(exports, module) {
    "use strict";
    var outside = require_outside();
    var ltr = (version, range, options) => outside(version, range, "<", options);
    module.exports = ltr;
  }
});

// node_modules/semver/ranges/intersects.js
var require_intersects = __commonJS({
  "node_modules/semver/ranges/intersects.js"(exports, module) {
    "use strict";
    var Range = require_range();
    var intersects = (r1, r2, options) => {
      r1 = new Range(r1, options);
      r2 = new Range(r2, options);
      return r1.intersects(r2, options);
    };
    module.exports = intersects;
  }
});

// node_modules/semver/ranges/simplify.js
var require_simplify = __commonJS({
  "node_modules/semver/ranges/simplify.js"(exports, module) {
    "use strict";
    var satisfies = require_satisfies();
    var compare2 = require_compare();
    module.exports = (versions, range, options) => {
      const set = [];
      let first = null;
      let prev = null;
      const v = versions.sort((a, b) => compare2(a, b, options));
      for (const version of v) {
        const included = satisfies(version, range, options);
        if (included) {
          prev = version;
          if (!first) {
            first = version;
          }
        } else {
          if (prev) {
            set.push([first, prev]);
          }
          prev = null;
          first = null;
        }
      }
      if (first) {
        set.push([first, null]);
      }
      const ranges = [];
      for (const [min, max] of set) {
        if (min === max) {
          ranges.push(min);
        } else if (!max && min === v[0]) {
          ranges.push("*");
        } else if (!max) {
          ranges.push(`>=${min}`);
        } else if (min === v[0]) {
          ranges.push(`<=${max}`);
        } else {
          ranges.push(`${min} - ${max}`);
        }
      }
      const simplified = ranges.join(" || ");
      const original = typeof range.raw === "string" ? range.raw : String(range);
      return simplified.length < original.length ? simplified : range;
    };
  }
});

// node_modules/semver/ranges/subset.js
var require_subset = __commonJS({
  "node_modules/semver/ranges/subset.js"(exports, module) {
    "use strict";
    var Range = require_range();
    var Comparator = require_comparator();
    var { ANY } = Comparator;
    var satisfies = require_satisfies();
    var compare2 = require_compare();
    var subset = (sub, dom, options = {}) => {
      if (sub === dom) {
        return true;
      }
      sub = new Range(sub, options);
      dom = new Range(dom, options);
      let sawNonNull = false;
      OUTER: for (const simpleSub of sub.set) {
        for (const simpleDom of dom.set) {
          const isSub = simpleSubset(simpleSub, simpleDom, options);
          sawNonNull = sawNonNull || isSub !== null;
          if (isSub) {
            continue OUTER;
          }
        }
        if (sawNonNull) {
          return false;
        }
      }
      return true;
    };
    var minimumVersionWithPreRelease = [new Comparator(">=0.0.0-0")];
    var minimumVersion = [new Comparator(">=0.0.0")];
    var simpleSubset = (sub, dom, options) => {
      if (sub === dom) {
        return true;
      }
      if (sub.length === 1 && sub[0].semver === ANY) {
        if (dom.length === 1 && dom[0].semver === ANY) {
          return true;
        } else if (options.includePrerelease) {
          sub = minimumVersionWithPreRelease;
        } else {
          sub = minimumVersion;
        }
      }
      if (dom.length === 1 && dom[0].semver === ANY) {
        if (options.includePrerelease) {
          return true;
        } else {
          dom = minimumVersion;
        }
      }
      const eqSet = /* @__PURE__ */ new Set();
      let gt, lt;
      for (const c of sub) {
        if (c.operator === ">" || c.operator === ">=") {
          gt = higherGT(gt, c, options);
        } else if (c.operator === "<" || c.operator === "<=") {
          lt = lowerLT(lt, c, options);
        } else {
          eqSet.add(c.semver);
        }
      }
      if (eqSet.size > 1) {
        return null;
      }
      let gtltComp;
      if (gt && lt) {
        gtltComp = compare2(gt.semver, lt.semver, options);
        if (gtltComp > 0) {
          return null;
        } else if (gtltComp === 0 && (gt.operator !== ">=" || lt.operator !== "<=")) {
          return null;
        }
      }
      for (const eq of eqSet) {
        if (gt && !satisfies(eq, String(gt), options)) {
          return null;
        }
        if (lt && !satisfies(eq, String(lt), options)) {
          return null;
        }
        for (const c of dom) {
          if (!satisfies(eq, String(c), options)) {
            return false;
          }
        }
        return true;
      }
      let higher, lower;
      let hasDomLT, hasDomGT;
      let needDomLTPre = lt && !options.includePrerelease && lt.semver.prerelease.length ? lt.semver : false;
      let needDomGTPre = gt && !options.includePrerelease && gt.semver.prerelease.length ? gt.semver : false;
      if (needDomLTPre && needDomLTPre.prerelease.length === 1 && lt.operator === "<" && needDomLTPre.prerelease[0] === 0) {
        needDomLTPre = false;
      }
      for (const c of dom) {
        hasDomGT = hasDomGT || c.operator === ">" || c.operator === ">=";
        hasDomLT = hasDomLT || c.operator === "<" || c.operator === "<=";
        if (gt) {
          if (needDomGTPre) {
            if (c.semver.prerelease && c.semver.prerelease.length && c.semver.major === needDomGTPre.major && c.semver.minor === needDomGTPre.minor && c.semver.patch === needDomGTPre.patch) {
              needDomGTPre = false;
            }
          }
          if (c.operator === ">" || c.operator === ">=") {
            higher = higherGT(gt, c, options);
            if (higher === c && higher !== gt) {
              return false;
            }
          } else if (gt.operator === ">=" && !c.test(gt.semver)) {
            return false;
          }
        }
        if (lt) {
          if (needDomLTPre) {
            if (c.semver.prerelease && c.semver.prerelease.length && c.semver.major === needDomLTPre.major && c.semver.minor === needDomLTPre.minor && c.semver.patch === needDomLTPre.patch) {
              needDomLTPre = false;
            }
          }
          if (c.operator === "<" || c.operator === "<=") {
            lower = lowerLT(lt, c, options);
            if (lower === c && lower !== lt) {
              return false;
            }
          } else if (lt.operator === "<=" && !c.test(lt.semver)) {
            return false;
          }
        }
        if (!c.operator && (lt || gt) && gtltComp !== 0) {
          return false;
        }
      }
      if (gt && hasDomLT && !lt && gtltComp !== 0) {
        return false;
      }
      if (lt && hasDomGT && !gt && gtltComp !== 0) {
        return false;
      }
      if (needDomGTPre || needDomLTPre) {
        return false;
      }
      return true;
    };
    var higherGT = (a, b, options) => {
      if (!a) {
        return b;
      }
      const comp = compare2(a.semver, b.semver, options);
      return comp > 0 ? a : comp < 0 ? b : b.operator === ">" && a.operator === ">=" ? b : a;
    };
    var lowerLT = (a, b, options) => {
      if (!a) {
        return b;
      }
      const comp = compare2(a.semver, b.semver, options);
      return comp < 0 ? a : comp > 0 ? b : b.operator === "<" && a.operator === "<=" ? b : a;
    };
    module.exports = subset;
  }
});

// node_modules/semver/index.js
var require_semver2 = __commonJS({
  "node_modules/semver/index.js"(exports, module) {
    "use strict";
    var internalRe = require_re();
    var constants4 = require_constants();
    var SemVer = require_semver();
    var identifiers = require_identifiers();
    var parse = require_parse();
    var valid = require_valid();
    var clean = require_clean();
    var inc = require_inc();
    var diff = require_diff();
    var major = require_major();
    var minor = require_minor();
    var patch = require_patch();
    var prerelease = require_prerelease();
    var compare2 = require_compare();
    var rcompare = require_rcompare();
    var compareLoose = require_compare_loose();
    var compareBuild = require_compare_build();
    var sort = require_sort();
    var rsort = require_rsort();
    var gt = require_gt();
    var lt = require_lt();
    var eq = require_eq();
    var neq = require_neq();
    var gte = require_gte();
    var lte = require_lte();
    var cmp = require_cmp();
    var coerce = require_coerce();
    var truncate = require_truncate();
    var Comparator = require_comparator();
    var Range = require_range();
    var satisfies = require_satisfies();
    var toComparators = require_to_comparators();
    var maxSatisfying = require_max_satisfying();
    var minSatisfying = require_min_satisfying();
    var minVersion = require_min_version();
    var validRange = require_valid2();
    var outside = require_outside();
    var gtr = require_gtr();
    var ltr = require_ltr();
    var intersects = require_intersects();
    var simplifyRange = require_simplify();
    var subset = require_subset();
    module.exports = {
      parse,
      valid,
      clean,
      inc,
      diff,
      major,
      minor,
      patch,
      prerelease,
      compare: compare2,
      rcompare,
      compareLoose,
      compareBuild,
      sort,
      rsort,
      gt,
      lt,
      eq,
      neq,
      gte,
      lte,
      cmp,
      coerce,
      truncate,
      Comparator,
      Range,
      satisfies,
      toComparators,
      maxSatisfying,
      minSatisfying,
      minVersion,
      validRange,
      outside,
      gtr,
      ltr,
      intersects,
      simplifyRange,
      subset,
      SemVer,
      re: internalRe.re,
      src: internalRe.src,
      tokens: internalRe.t,
      SEMVER_SPEC_VERSION: constants4.SEMVER_SPEC_VERSION,
      RELEASE_TYPES: constants4.RELEASE_TYPES,
      compareIdentifiers: identifiers.compareIdentifiers,
      rcompareIdentifiers: identifiers.rcompareIdentifiers
    };
  }
});

// .plugin/runtime/main.ts
import path5 from "path";
import fs3 from "fs/promises";
import { fileURLToPath as fileURLToPath2 } from "url";

// .plugin/runtime/resolve.ts
import fs from "fs/promises";
import { constants as constants2 } from "fs";
import path from "path";
import os from "os";
import { fileURLToPath } from "url";

// packages/cli/src/utils/semver.ts
var import_semver = __toESM(require_semver2(), 1);
function compareVersions(left, right) {
  return (0, import_semver.compare)(left, right);
}

// .plugin/runtime/process.ts
import { spawn } from "child_process";
import { constants } from "os";

// packages/cli/src/utils/logger.ts
import { AsyncLocalStorage } from "async_hooks";
var stderrDebugLogs = new AsyncLocalStorage();
function withStderrDebugLogs(action) {
  return stderrDebugLogs.run(true, action);
}
function debugLog(message) {
  if (process.env.DEVECO_CLI_DEBUG) {
    const msg = typeof message === "function" ? message() : message;
    if (stderrDebugLogs.getStore()) {
      console.error(`[DEBUG] ${msg}`);
    } else {
      console.log(`[DEBUG] ${msg}`);
    }
  }
}

// .plugin/runtime/process.ts
function forwardInterrupts(child) {
  let interrupted;
  const handlers = /* @__PURE__ */ new Map();
  for (const signal of ["SIGINT", "SIGTERM"]) {
    const handler = () => {
      if (child.exitCode !== null || child.signalCode !== null) {
        return;
      }
      if (interrupted) {
        child.kill("SIGKILL");
        return;
      }
      interrupted = signal;
      if (process.platform !== "win32" || signal !== "SIGINT") {
        child.kill(signal);
      }
      console.error(
        "Waiting for the command to finish. Interrupt again to force termination."
      );
    };
    handlers.set(signal, handler);
    process.on(signal, handler);
  }
  return () => {
    for (const [signal, handler] of handlers) {
      process.off(signal, handler);
    }
  };
}
function runProcess(command, args, options = {}) {
  debugLog(`Executing: ${command} ${args.join(" ")}`);
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: options.capture ? ["ignore", "pipe", "pipe"] : "inherit",
      windowsHide: true,
      ...options,
      shell: false
    });
    let stdout = "";
    let stderr = "";
    const clean = forwardInterrupts(child);
    child.stdout?.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr?.on("data", (chunk) => {
      stderr += chunk;
    });
    child.once("error", (error) => {
      clean();
      reject(error);
    });
    child.once("close", (code, signal) => {
      clean();
      const exitCode = code ?? (signal ? 128 + (constants.signals[signal] || 1) : 1);
      resolve({ exitCode, stdout, stderr });
    });
  });
}

// .plugin/runtime/resolve.ts
var WRAPPER_MARKER = "deveco-cli-plugin-entry";
var SEMVER = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/;
var LABELS = {
  host: "host-managed",
  path: "global",
  private: "plugin-managed"
};
var RuntimeUnavailableError = class extends Error {
  constructor(message, skipped) {
    super(message);
    this.skipped = skipped;
    this.name = "RuntimeUnavailableError";
  }
};
var HostContextError = class extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name = "HostContextError";
  }
};
function installRoot(metadata, env = process.env, platform = process.platform) {
  const root = env.DEVECO_PLUGIN_INSTALL_ROOT;
  if (root && !path.isAbsolute(root)) {
    throw new Error("DEVECO_PLUGIN_INSTALL_ROOT must be an absolute path.");
  }
  const home = platform === metadata.harmonyos.platform ? env.HOME || metadata.harmonyos.homeDirectory : userHome(env, platform);
  return root || path.join(home, ...metadata.installRoot.split("/"));
}
function userHome(env = process.env, platform = process.platform) {
  return (platform === "win32" ? env.USERPROFILE : env.HOME) || os.homedir();
}
function harmonyRequiredFiles(metadata) {
  return [
    metadata.harmonyos.nodeRelativePath,
    "ohpm/bin/pm-cli.js",
    "hvigor/bin/hvigorw.js",
    "sdk/default/openharmony/toolchains/hdc"
  ];
}
function contained(root, file) {
  const relative = path.relative(root, file);
  return relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}
async function validateHarmonyToolchain(root, metadata) {
  const rootStat = await fs.lstat(root).catch(() => null);
  if (!rootStat?.isDirectory() || rootStat.isSymbolicLink()) {
    throw new Error("root is not an ordinary directory");
  }
  const canonicalRoot = await fs.realpath(root);
  for (const relative of harmonyRequiredFiles(metadata)) {
    const configured = path.join(root, ...relative.split("/"));
    const canonical = await fs.realpath(configured).catch(() => null);
    if (!canonical || !contained(canonicalRoot, canonical)) {
      throw new Error(`${relative} escapes or is missing`);
    }
    if (!(await fs.stat(canonical)).isFile()) {
      throw new Error(`${relative} is not a regular file`);
    }
  }
  return canonicalRoot;
}
async function nodeSupported(root, metadata) {
  const node = path.join(
    root,
    ...metadata.harmonyos.nodeRelativePath.split("/")
  );
  const result = await runProcess(node, ["-p", "process.versions.node"], {
    capture: true,
    timeout: 1e4
  }).catch(() => null);
  const version = result?.exitCode === 0 ? result.stdout.trim() : "";
  const major = Number(version.split(".")[0]);
  return version !== "" && Number.isInteger(major) && major >= metadata.nodeMajorMinimum;
}
function parseToolchainVersion(name, prefix) {
  const suffix = name.slice(prefix.length);
  if (!/^\d+(?:\.\d+)*$/.test(suffix)) {
    return null;
  }
  return suffix.split(".").map(Number);
}
function parseTrailingVersion(name) {
  const match = name.match(/(\d+(?:\.\d+)*)$/);
  return match ? match[1].split(".").map(Number) : null;
}
function compareToolchainVersions(left, right) {
  const length = Math.max(left.length, right.length);
  for (let index = 0; index < length; index++) {
    const difference = (left[index] ?? 0) - (right[index] ?? 0);
    if (difference) {
      return difference;
    }
  }
  return 0;
}
function assertDistinctVersions(candidates) {
  for (let index = 1; index < candidates.length; index++) {
    if (compareToolchainVersions(
      candidates[index - 1].version,
      candidates[index].version
    ) === 0) {
      throw new HostContextError(
        "configuration-error",
        `HarmonyOS toolchain versions are ambiguous: ${path.basename(candidates[index - 1].root)} and ${path.basename(candidates[index].root)}`
      );
    }
  }
}
function partitionToolchainEntries(entries, directory, prefix) {
  const candidates = [];
  const skippedNames = [];
  for (const entry of entries) {
    if (!entry.name.startsWith(prefix) || !(entry.isDirectory() || entry.isSymbolicLink())) {
      continue;
    }
    const version = parseToolchainVersion(entry.name, prefix);
    if (!version) {
      skippedNames.push(entry.name);
      continue;
    }
    candidates.push({
      root: path.join(directory, entry.name),
      source: "user",
      version
    });
  }
  return { candidates, skippedNames };
}
async function discoverHarmonyToolchains(roots, metadata) {
  const discovered = [];
  const visited = /* @__PURE__ */ new Set();
  const requiredNode = metadata.harmonyos.nodeRelativePath;
  async function walk(directory, depth) {
    if (depth > 8 || visited.has(directory)) {
      return;
    }
    visited.add(directory);
    const entries = await fs.readdir(directory, { withFileTypes: true }).catch(() => []);
    const nodePath = path.join(directory, ...requiredNode.split("/"));
    if ((await fs.stat(nodePath).catch(() => null))?.isFile()) {
      discovered.push({
        root: directory,
        source: "user",
        version: parseTrailingVersion(path.basename(directory)) ?? [0]
      });
      return;
    }
    for (const entry of entries) {
      if (entry.isDirectory() && !entry.isSymbolicLink()) {
        await walk(path.join(directory, entry.name), depth + 1);
      }
    }
  }
  for (const root of roots) {
    if ((await fs.stat(root).catch(() => null))?.isDirectory()) {
      await walk(root, 0);
    }
  }
  return discovered;
}
async function userToolchainCandidates(metadata, env) {
  const { userToolchainDirectory, userToolchainPrefix } = metadata.harmonyos;
  const fixedRoot = path.join(userToolchainDirectory, "command-line-tools");
  const directoryStat = await fs.lstat(userToolchainDirectory).catch((error) => {
    if (error.code === "ENOENT" || error.code === "EACCES") {
      return null;
    }
    throw new HostContextError(
      "toolchain-invalid",
      `Cannot stat HarmonyOS toolchain directory: ${error.message}`
    );
  });
  if (!directoryStat) {
    const extracted2 = await discoverHarmonyToolchains(
      [metadata.harmonyos.homeDirectory, env.HOME ?? ""],
      metadata
    );
    return { candidates: extracted2, skippedNames: [] };
  }
  if (!directoryStat.isDirectory() || directoryStat.isSymbolicLink()) {
    throw new HostContextError(
      "toolchain-invalid",
      `HarmonyOS toolchain directory is not an ordinary directory: ${userToolchainDirectory}`
    );
  }
  const entries = await fs.readdir(userToolchainDirectory, { withFileTypes: true }).catch((error) => {
    throw new HostContextError(
      "toolchain-invalid",
      `Cannot read HarmonyOS toolchain directory: ${error.message}`
    );
  });
  const { candidates, skippedNames } = partitionToolchainEntries(
    entries,
    userToolchainDirectory,
    userToolchainPrefix
  );
  const fixedStat = await fs.lstat(fixedRoot).catch(() => null);
  if (fixedStat?.isDirectory() && !fixedStat.isSymbolicLink()) {
    candidates.push({
      root: fixedRoot,
      source: "user",
      version: [Number.MAX_SAFE_INTEGER]
    });
  }
  const extracted = await discoverHarmonyToolchains(
    [userToolchainDirectory, metadata.harmonyos.homeDirectory, env.HOME ?? ""],
    metadata
  );
  for (const candidate of extracted) {
    if (!candidates.some(
      (item) => path.resolve(item.root) === path.resolve(candidate.root)
    )) {
      candidates.push(candidate);
    }
  }
  candidates.sort(
    (left, right) => compareToolchainVersions(right.version, left.version)
  );
  assertDistinctVersions(candidates);
  return { candidates, skippedNames };
}
var errorMessage = (error) => error instanceof Error ? error.message : String(error);
async function selectHarmonyToolchain(metadata, env) {
  const systemRoot = metadata.harmonyos.systemToolchainRoot;
  const systemExists = (await fs.stat(systemRoot).catch(() => null))?.isDirectory() === true;
  let userCandidates = [];
  let skippedNames = [];
  const sandboxParent = metadata.harmonyos.downloadTargetDirectory;
  const sandboxRoot = path.join(sandboxParent, "command-line-tools");
  const systems = await discoverHarmonyToolchains([systemRoot], metadata);
  if (systemExists && systems.length === 0) {
    systems.push({
      root: systemRoot,
      source: "system",
      version: [0]
    });
  }
  systems.sort(
    (left, right) => compareToolchainVersions(right.version, left.version)
  );
  const privateCandidates = [sandboxRoot, sandboxParent].map((root) => ({
    root,
    source: "user",
    version: [0]
  }));
  const ordered = [
    ...systems.map((candidate) => ({
      ...candidate,
      source: "system"
    })),
    ...privateCandidates
  ];
  const invalid = [];
  let searchedExternal = false;
  for (let index = 0; ; index++) {
    if (index === ordered.length && !searchedExternal) {
      ({ candidates: userCandidates, skippedNames } = await userToolchainCandidates(metadata, env));
      ordered.push(
        ...userCandidates.filter(
          (candidate2) => !contained(systemRoot, candidate2.root) && !contained(sandboxParent, candidate2.root)
        )
      );
      searchedExternal = true;
    }
    if (index >= ordered.length) {
      break;
    }
    const candidate = ordered[index];
    try {
      let root = await validateHarmonyToolchain(candidate.root, metadata);
      if (candidate.source !== "system" && !contained(
        await fs.realpath(sandboxParent).catch(() => sandboxParent),
        root
      )) {
        const bootstrap = fileURLToPath(
          new URL("../bin/devecocli-bootstrap", import.meta.url)
        );
        const imported = await runProcess(
          "/bin/sh",
          [
            "-c",
            '. "$1"; deveco_import_harmony_toolchain "$2" "$3" "$4" "$5"',
            "deveco-clt-import",
            bootstrap,
            root,
            sandboxRoot,
            metadata.harmonyos.nodeRelativePath,
            String(metadata.nodeMajorMinimum)
          ],
          {
            env: {
              ...process.env,
              ...env,
              HOME: env.HOME || metadata.harmonyos.homeDirectory
            }
          }
        );
        if (imported.exitCode !== 0) {
          throw new Error(`CLT import failed (exit ${imported.exitCode})`);
        }
        root = await validateHarmonyToolchain(sandboxRoot, metadata);
      }
      if (!await nodeSupported(root, metadata)) {
        throw new Error(
          `node is below the minimum ${metadata.nodeMajorMinimum}`
        );
      }
      const node = await fs.realpath(
        path.join(root, ...metadata.harmonyos.nodeRelativePath.split("/"))
      );
      return {
        root,
        node,
        source: candidate.source
      };
    } catch (error) {
      invalid.push(`${candidate.root}: ${errorMessage(error)}`);
    }
  }
  const skipped = skippedNames.length ? ` Skipped unparsable toolchain directories: ${skippedNames.join(", ")}.` : "";
  if (!systemExists && userCandidates.length + skippedNames.length === 0) {
    throw new HostContextError(
      "toolchain-required",
      "Neither DevEco Studio nor HarmonyOS Command Line Tools is installed."
    );
  }
  throw new HostContextError(
    "toolchain-invalid",
    `No valid HarmonyOS toolchain was found.${skipped} ${invalid.join("; ")}`
  );
}
async function resolveHostContext(metadata, env = process.env, platform = process.platform) {
  const bootstrapVariant = env.DEVECO_PLUGIN_BOOTSTRAP_VARIANT;
  if (!["win32", "darwin", "linux", metadata.harmonyos.platform].includes(
    platform
  )) {
    throw new HostContextError(
      "unsupported-host",
      `Unsupported plugin host: ${platform}.`
    );
  }
  if (platform !== metadata.harmonyos.platform) {
    if (bootstrapVariant === "harmonyos-native") {
      throw new HostContextError(
        "configuration-error",
        `The launcher reported HarmonyOS, but Node reported ${platform}.`
      );
    }
    return {
      platform,
      runtimeVariant: "cross-platform",
      toolchain: null
    };
  }
  return resolveHarmonyHostContext(metadata, env, bootstrapVariant);
}
function runtimeEnvironment(metadata, host, input = process.env) {
  const env = { ...input };
  if (!host.toolchain) {
    const nodeBin = path.dirname(process.execPath);
    env.PATH = [env.PATH || env.Path || "", nodeBin].filter(Boolean).join(path.delimiter);
    delete env.Path;
    env.DEVECO_PLUGIN_RUNTIME_NODE = process.execPath;
    return env;
  }
  const bin = path.dirname(host.toolchain.node);
  env.HOME = env.HOME || metadata.harmonyos.homeDirectory;
  env.DEVECO_CLI_DATA_DIR = path.join(env.HOME, ".config", "deveco-cli");
  env.PATH = [bin, env.PATH || env.Path || ""].filter(Boolean).join(path.delimiter);
  delete env.Path;
  env.DEVECO_PLUGIN_RUNTIME_NODE = host.toolchain.node;
  env.COMMAND_LINE_TOOL_PATH = host.toolchain.root;
  env.DEVECO_CLI_CLT_PATH = host.toolchain.root;
  return env;
}
async function resolveHarmonyHostContext(metadata, env, bootstrapVariant) {
  if (bootstrapVariant && bootstrapVariant !== "harmonyos-native") {
    throw new HostContextError(
      "configuration-error",
      `The launcher reported ${bootstrapVariant}, but Node reported HarmonyOS.`
    );
  }
  return {
    platform: metadata.harmonyos.platform,
    runtimeVariant: "harmonyos-native",
    toolchain: await selectHarmonyToolchain(metadata, env)
  };
}
function isSemver(version) {
  return typeof version === "string" && SEMVER.test(version);
}
function meetsMinimum(version, minimum) {
  return isSemver(version) && compareVersions(version, minimum) >= 0;
}
async function readJson(file) {
  return JSON.parse(await fs.readFile(file, "utf8"));
}
async function executable(file) {
  try {
    if (!(await fs.stat(file)).isFile()) {
      return false;
    }
    await fs.access(
      file,
      process.platform === "win32" ? constants2.F_OK : constants2.X_OK
    );
    return true;
  } catch {
    return false;
  }
}
async function inspectExecutable(file, nodeExecutable = process.execPath) {
  if (/\.(?:c?js|mjs)$/i.test(file)) {
    if (!(await fs.stat(file).catch(() => null))?.isFile()) {
      return null;
    }
  } else if (!await executable(file)) {
    return null;
  }
  const real = await fs.realpath(file);
  const ext = path.extname(real).toLowerCase();
  if (ext === ".exe") {
    return { command: real, args: [], entry: real };
  }
  const handle = await fs.open(real);
  let text;
  try {
    const buffer = Buffer.alloc(8192);
    const { bytesRead } = await handle.read(buffer, 0, buffer.length, 0);
    text = buffer.toString("utf8", 0, bytesRead);
  } finally {
    await handle.close();
  }
  if (text.includes(WRAPPER_MARKER)) {
    return { wrapper: true };
  }
  if (ext === ".cmd" || ext === ".bat") {
    const match = text.match(/"%dp0%[\\/]([^"\r\n]+\.(?:c?js|mjs))"/i);
    if (!match) {
      return null;
    }
    const entry = path.resolve(
      path.dirname(real),
      match[1].replaceAll("\\", "/")
    );
    if (!(await fs.stat(entry).catch(() => null))?.isFile()) {
      return null;
    }
    return { command: nodeExecutable, args: [entry], entry };
  }
  if (/\.(?:c?js|mjs)$/.test(ext) || /^#!.*\bnode\b/.test(text)) {
    return { command: nodeExecutable, args: [real], entry: real };
  }
  return process.platform === "win32" ? null : { command: real, args: [], entry: real };
}
async function resolveExecutable(file, nodeExecutable = process.execPath) {
  const found = await inspectExecutable(file, nodeExecutable);
  return found?.wrapper ? null : found;
}
var samePath = (left, right) => process.platform === "win32" ? left.toLowerCase() === right.toLowerCase() : left === right;
async function entryPackage(entry) {
  let dir = path.dirname(entry);
  for (let depth = 0; depth < 3; depth++) {
    const pkg = await readJson(path.join(dir, "package.json")).catch(
      () => null
    );
    const bin = pkg?.bin?.devecocli;
    if (typeof bin === "string" && samePath(path.resolve(dir, bin), entry)) {
      return {
        root: dir,
        name: pkg.name,
        version: pkg.version,
        os: pkg.os,
        cpu: pkg.cpu,
        optionalDependencies: pkg.optionalDependencies
      };
    }
    dir = path.dirname(dir);
  }
  return null;
}
function implementationForHost(metadata, platform = process.platform, arch = process.arch) {
  const matches = (metadata.implementations ?? []).filter(
    ({ os: os2, cpu }) => os2.includes(platform) && cpu.includes(arch)
  );
  if (matches.length !== 1) {
    throw new Error(
      `No unique DevEco CLI implementation is declared for ${platform}/${arch}.`
    );
  }
  return matches[0];
}
async function packageAt(root) {
  const pkg = await readJson(path.join(root, "package.json")).catch(() => null);
  return pkg ? { root, ...pkg } : null;
}
async function findDependencyPackage(wrapperRoot, packageName) {
  const segments = packageName.split("/");
  const candidates = [path.join(wrapperRoot, "node_modules", ...segments)];
  let directory = wrapperRoot;
  for (let depth = 0; depth < 6; depth++) {
    candidates.push(path.join(directory, "node_modules", ...segments));
    directory = path.dirname(directory);
  }
  for (const candidate of [...new Set(candidates)]) {
    const pkg = await packageAt(candidate);
    if (pkg) {
      return pkg;
    }
  }
  return null;
}
function assertImplementationPackage(pkg, expected, platform, arch) {
  if (pkg.name !== expected.packageName || !meetsMinimum(
    typeof pkg.version === "string" ? pkg.version : null,
    expected.packageVersion
  )) {
    throw new Error(
      `DevEco CLI implementation mismatch: expected ${expected.packageName}@${expected.packageVersion} or later.`
    );
  }
  if (!expected.os.includes(platform) || !expected.cpu.includes(arch)) {
    throw new Error(
      `${expected.packageName} is not compatible with ${platform}/${arch}.`
    );
  }
  const packageOs = Array.isArray(pkg.os) ? [...pkg.os].sort() : [];
  const packageCpu = Array.isArray(pkg.cpu) ? [...pkg.cpu].sort() : [];
  if (JSON.stringify(packageOs) !== JSON.stringify([...expected.os].sort()) || JSON.stringify(packageCpu) !== JSON.stringify([...expected.cpu].sort())) {
    throw new Error(
      `DevEco CLI implementation platform metadata mismatch: ${expected.packageName}.`
    );
  }
}
async function identifyRuntime(metadata, runtime, platform = process.platform, arch = process.arch) {
  if (!metadata.wrapper || !metadata.implementations?.length) {
    return runtime;
  }
  const owner = await entryPackage(runtime.entry);
  if (!owner) {
    throw new Error(
      `Runtime entry is not owned by a supported npm package: ${runtime.entry}.`
    );
  }
  const expected = implementationForHost(metadata, platform, arch);
  if (owner.name === metadata.wrapper.name) {
    if (!meetsMinimum(owner.version, metadata.wrapper.version)) {
      throw new Error(
        `Unsupported DevEco CLI wrapper version ${owner.version}; this plugin requires ${metadata.wrapper.version} or later.`
      );
    }
    const dependencyVersion = owner.optionalDependencies?.[expected.packageName] ?? null;
    const floatingDependency = dependencyVersion === "daily" || dependencyVersion === "latest";
    if (!floatingDependency && !meetsMinimum(dependencyVersion, expected.packageVersion)) {
      throw new Error(
        `The DevEco CLI wrapper does not declare ${expected.packageName}@${expected.packageVersion} or later.`
      );
    }
    const implementation = await findDependencyPackage(
      owner.root,
      expected.packageName
    );
    if (!implementation) {
      throw new Error(
        `The selected implementation package is missing: ${expected.packageName}.`
      );
    }
    assertImplementationPackage(implementation, expected, platform, arch);
    if (!meetsMinimum(implementation.version, expected.packageVersion) || !floatingDependency && implementation.version !== dependencyVersion) {
      throw new Error(
        `The installed ${expected.packageName} version does not match the wrapper dependency.`
      );
    }
    return {
      ...runtime,
      implementation: {
        kind: expected.id,
        skillReference: expected.skillReference
      }
    };
  }
  const direct = metadata.implementations.find(
    ({ packageName }) => packageName === owner.name
  );
  if (!direct) {
    throw new Error(`Unsupported DevEco CLI package: ${owner.name}.`);
  }
  assertImplementationPackage(owner, direct, platform, arch);
  if (direct.id !== expected.id) {
    throw new Error(
      `${owner.name} is the wrong implementation for ${platform}/${arch}.`
    );
  }
  return {
    ...runtime,
    implementation: {
      kind: direct.id,
      skillReference: direct.skillReference
    }
  };
}
async function runtimeCliVersion(metadata, runtime) {
  if (process.platform !== metadata.harmonyos.platform) {
    return runtime.version;
  }
  const owner = await entryPackage(runtime.entry);
  if (!owner || owner.name !== metadata.wrapper?.name) {
    return runtime.version;
  }
  const expected = implementationForHost(metadata);
  return (await findDependencyPackage(owner.root, expected.packageName))?.version ?? null;
}
async function managedRuntime(root, packageName, nodeExecutable = process.execPath) {
  const state = await readJson(path.join(root, "current.json")).catch(
    (error) => {
      if (error.code === "ENOENT") {
        return null;
      }
      throw new Error(`Cannot read private Runtime state: ${error.message}`);
    }
  );
  if (!state || state.packageName !== packageName) {
    return null;
  }
  if (!/^[a-f0-9-]{36}$/.test(state.installId)) {
    throw new Error("Invalid private Runtime install ID.");
  }
  const packageRoot = path.join(
    root,
    "installs",
    state.installId,
    "node_modules",
    packageName
  );
  const pkg = await readJson(path.join(packageRoot, "package.json"));
  const binEntry = pkg.bin?.devecocli;
  if (pkg.name !== packageName || typeof binEntry !== "string") {
    throw new Error(
      "Invalid private DevEco CLI package. Run devecocli-install to repair it."
    );
  }
  const entry = path.join(packageRoot, binEntry);
  if (!(await fs.stat(entry)).isFile()) {
    throw new Error(`Runtime entry is missing: ${entry}`);
  }
  return {
    command: nodeExecutable,
    args: [entry],
    entry,
    source: "private",
    version: pkg.version
  };
}
async function executableCandidates(dirs, source, nodeExecutable) {
  const candidates = [];
  const entries = /* @__PURE__ */ new Set();
  const names = process.platform === "win32" ? ["devecocli.cmd", "devecocli.exe"] : ["devecocli"];
  for (const dir of dirs) {
    if (!path.isAbsolute(dir)) {
      continue;
    }
    for (const name of names) {
      const found = await inspectExecutable(
        path.join(dir, name),
        nodeExecutable
      );
      if (found && !found.wrapper && !entries.has(found.entry)) {
        entries.add(found.entry);
        candidates.push({ ...found, source });
      }
    }
  }
  return candidates;
}
async function withVersion(runtime) {
  if (!runtime) {
    return null;
  }
  const version = runtime.version ?? (await entryPackage(runtime.entry))?.version ?? null;
  return { ...runtime, version };
}
var describe = ({ source, entry, version }) => `the ${LABELS[source]} DevEco CLI at ${entry} (version ${version || "unknown"})`;
function runtimeLocations(metadata, env = process.env, platform = process.platform) {
  const harmonyNpmBin = platform === metadata.harmonyos.platform ? path.join(metadata.harmonyos.homeDirectory, "npm/bin") : null;
  return [
    ...harmonyNpmBin ? [{ dirs: [harmonyNpmBin], source: "host" }] : [],
    {
      dirs: [path.join(metadata.hostConfigDirectory, "bin")],
      source: "host"
    },
    {
      dirs: (env.PATH || env.Path || "").split(path.delimiter).filter(Boolean),
      source: "path"
    }
  ];
}
async function meetsRuntimeMinimum(metadata, runtime) {
  const owner = await entryPackage(runtime.entry);
  const implementation = metadata.implementations?.find(
    ({ packageName }) => packageName === owner?.name
  );
  return meetsMinimum(
    runtime.version,
    implementation?.packageVersion ?? metadata.minimumVersion
  );
}
async function resolveRuntime(metadata, env = process.env) {
  const nodeExecutable = env.DEVECO_PLUGIN_RUNTIME_NODE || process.execPath;
  const explicit = env.DEVECO_PLUGIN_RUNTIME_EXECUTABLE;
  if (explicit) {
    if (!path.isAbsolute(explicit)) {
      throw new Error("DEVECO_PLUGIN_RUNTIME_EXECUTABLE must be absolute.");
    }
    const found = await resolveExecutable(explicit, nodeExecutable);
    if (!found) {
      throw new Error(
        `Invalid Runtime entry: ${explicit}. Use the real CLI entry, not the plugin wrapper.`
      );
    }
    const selected2 = {
      ...found,
      source: "explicit",
      version: (await entryPackage(found.entry))?.version ?? null
    };
    if (!await meetsRuntimeMinimum(metadata, selected2)) {
      throw new Error(
        `The explicit Runtime version does not meet ${metadata.minimumVersion}.`
      );
    }
    return { ...await identifyRuntime(metadata, selected2), skipped: [] };
  }
  const locations = runtimeLocations(metadata, env);
  const skipped = [];
  let selected = null;
  for (const { dirs, source } of locations) {
    const candidates = await executableCandidates(dirs, source, nodeExecutable);
    for (const runtime of candidates) {
      const candidate = await withVersion(runtime);
      if (!candidate) {
        continue;
      }
      if (await meetsRuntimeMinimum(metadata, candidate)) {
        try {
          selected = await identifyRuntime(metadata, candidate);
          break;
        } catch {
          skipped.push(candidate);
          continue;
        }
      }
      skipped.push(candidate);
    }
    if (selected) {
      break;
    }
  }
  if (!selected) {
    const managed = await managedRuntime(
      installRoot(metadata, env),
      metadata.packageName,
      nodeExecutable
    );
    const skippedText = skipped.length ? ` Skipped ${skipped.map(describe).join("; ")}: below the minimum version ${metadata.minimumVersion}. Skipped CLIs are left unchanged.` : "";
    if (!managed) {
      throw new RuntimeUnavailableError(
        `No DevEco CLI meeting the minimum version ${metadata.minimumVersion} is installed.${skippedText} Run devecocli-install after authorizing the Runtime installation; it installs into the plugin-managed directory only.`,
        skipped
      );
    }
    if (!await meetsRuntimeMinimum(metadata, managed)) {
      throw new RuntimeUnavailableError(
        `${describe(managed).replace(/^t/, "T")} is below the minimum version ${metadata.minimumVersion} required by this plugin.${skippedText} Run devecocli-install within the user's authorization to update it.`,
        [...skipped, managed]
      );
    }
    selected = await identifyRuntime(metadata, managed);
  }
  return {
    ...selected,
    skipped: skipped.map(({ source, entry, version }) => ({
      source,
      entry,
      version
    }))
  };
}

// .plugin/runtime/check-report.ts
import path2 from "path";
var errorMessage2 = (error) => error instanceof Error ? error.message : String(error);
function toolchainActions(metadata, pluginRoot2) {
  return [
    {
      action: "choose-toolchain",
      options: {
        devecoStudio: {
          source: metadata.harmonyos.studioInstallSource,
          search: metadata.harmonyos.studioInstallSearch,
          actions: [
            { action: "ask-user-to-install-from-appgallery" },
            { action: "rerun-runtime-check" }
          ]
        },
        commandLineTools: {
          actions: [
            {
              action: "open-built-in-browser",
              url: metadata.harmonyos.downloadUrl
            },
            {
              action: "run",
              command: path2.join(
                pluginRoot2,
                "bin/devecocli-clt-install-after-browser-start"
              ),
              waitForCompletion: false
            },
            { action: "poll-log-for-task-result-until-complete" },
            { action: "rerun-runtime-check" }
          ]
        }
      }
    }
  ];
}
function hostContextFailure(metadata, status, error, pluginRoot2) {
  const actionable = status === "toolchain-required" || status === "toolchain-invalid";
  const actions = status === "toolchain-required" ? toolchainActions(metadata, pluginRoot2) : [
    {
      action: status === "toolchain-invalid" ? "review-runtime-error" : status === "unsupported-host" ? "use-a-supported-host" : "repair-plugin-configuration"
    }
  ];
  return {
    exitCode: actionable ? 2 : 1,
    fields: {
      actions,
      error: { code: status, message: errorMessage2(error) }
    }
  };
}

// .plugin/runtime/client.ts
import path3 from "path";
function resolveClient(clients, pluginDirectory, env, platform = process.platform) {
  const paths = platform === "win32" ? path3.win32 : path3.posix;
  const normalized = platform === "win32" ? paths.normalize(pluginDirectory).replaceAll("\\", "/") : paths.normalize(pluginDirectory);
  const segments = normalized.split("/");
  const matches = clients.filter(
    ({ directory: directory2 }) => segments.some(
      (segment) => platform === "win32" ? segment.toLowerCase() === directory2.toLowerCase() : segment === directory2
    )
  );
  const override = env.DEVECO_PLUGIN_CLIENT;
  let candidates = override ? clients.filter(({ id }) => id === override) : matches;
  if (!override && !matches.length) {
    candidates = clients.filter(
      ({ configEnvironment }) => Boolean(env[configEnvironment])
    );
  }
  if (candidates.length !== 1) {
    throw new Error(
      "Cannot identify a unique Qoder client. Set DEVECO_PLUGIN_CLIENT to qoder or qoder-cn; HOME is not a client identifier."
    );
  }
  const profile = candidates[0];
  const marker = segments.findIndex(
    (segment) => platform === "win32" ? segment.toLowerCase() === profile.directory.toLowerCase() : segment === profile.directory
  );
  const directory = env[profile.configEnvironment] || (marker >= 0 ? segments.slice(0, marker + 1).join("/") : paths.join(userHome(env, platform), profile.directory));
  if (!paths.isAbsolute(directory)) {
    throw new Error(`${profile.configEnvironment} must be an absolute path.`);
  }
  return { profile, directory: paths.normalize(directory) };
}
function clientRuntimeMetadata(metadata, pluginDirectory, env = process.env) {
  if (!Array.isArray(metadata.clients) || metadata.clients.length === 0) {
    throw new Error("The plugin client configuration is missing.");
  }
  const { profile, directory } = resolveClient(
    metadata.clients,
    pluginDirectory,
    env
  );
  return {
    ...metadata,
    hostConfigDirectory: directory,
    taskNamespace: profile.id
  };
}

// .plugin/runtime/install.ts
import fs2 from "fs/promises";
import { constants as constants3 } from "fs";
import path4 from "path";
import { createHash, randomUUID } from "crypto";
var INSTALL_USAGE = "Usage: devecocli-install [--version <version-or-tag>]";
var NPM_FAILURE = 2;
function parseVersion(args, defaultVersion) {
  if (args.length === 0) {
    return defaultVersion;
  }
  if (args.length !== 2 || args[0] !== "--version" || !/^[a-zA-Z0-9][a-zA-Z0-9.+-]*$/.test(args[1])) {
    throw new Error(INSTALL_USAGE);
  }
  return args[1];
}
function assertMinimum(metadata, version, suffix = "") {
  if (!meetsMinimum(version, metadata.minimumVersion)) {
    throw new Error(
      `${metadata.packageName}@${version} is below the minimum version ${metadata.minimumVersion} required by this plugin.${suffix}`
    );
  }
}
async function npmInvocation(env = process.env, toolchainRoot, nodeExecutable = process.execPath) {
  if (toolchainRoot) {
    return harmonyNpmInvocation(toolchainRoot, nodeExecutable);
  }
  const dirs = [
    path4.dirname(process.execPath),
    ...(env.PATH || env.Path || "").split(path4.delimiter)
  ];
  for (const dir of dirs.filter(Boolean)) {
    for (const relative of [
      "node_modules/npm/bin/npm-cli.js",
      "../lib/node_modules/npm/bin/npm-cli.js"
    ]) {
      const entry = path4.resolve(dir, relative);
      if ((await fs2.stat(entry).catch(() => null))?.isFile()) {
        return { command: process.execPath, args: [entry] };
      }
    }
    const file = path4.resolve(dir, "npm");
    const real = await fs2.realpath(file).catch(() => null);
    if (real?.endsWith("npm-cli.js")) {
      return { command: process.execPath, args: [real] };
    }
  }
  throw new Error(
    "npm is required. Install a Node.js distribution that includes npm, then retry."
  );
}
async function npmPackageRoots(toolchainRoot, nodeExecutable) {
  const canonicalRoot = await fs2.realpath(toolchainRoot);
  const canonicalNode = await fs2.realpath(nodeExecutable).catch(() => null);
  if (!canonicalNode || !contained(canonicalRoot, canonicalNode)) {
    throw new Error(
      `The selected Node.js executable is outside the HarmonyOS toolchain: ${nodeExecutable}`
    );
  }
  const nodeDirectory = path4.dirname(canonicalNode);
  return {
    canonicalRoot,
    packageRoots: [
      path4.resolve(nodeDirectory, "../lib/node_modules/npm"),
      path4.resolve(nodeDirectory, "../node_modules/npm"),
      path4.resolve(nodeDirectory, "node_modules/npm")
    ]
  };
}
async function publicHarmonyNpm(canonicalRoot, nodeExecutable) {
  const npmExecutable = path4.join(path4.dirname(nodeExecutable), "npm");
  const canonicalNpmExecutable = await fs2.realpath(npmExecutable).catch(() => null);
  const npmExecutableReady = await fs2.access(npmExecutable, constants3.X_OK).then(() => true).catch(() => false);
  if (!canonicalNpmExecutable || !contained(canonicalRoot, canonicalNpmExecutable) || !(await fs2.stat(npmExecutable).catch(() => null))?.isFile() || !npmExecutableReady) {
    return null;
  }
  return { command: npmExecutable, args: [] };
}
async function harmonyNpmInvocation(toolchainRoot, nodeExecutable) {
  const { canonicalRoot, packageRoots } = await npmPackageRoots(
    toolchainRoot,
    nodeExecutable
  );
  const publicNpm = await publicHarmonyNpm(canonicalRoot, nodeExecutable);
  if (publicNpm) {
    return publicNpm;
  }
  for (const packageRoot of packageRoots) {
    const canonicalPackageRoot = await fs2.realpath(packageRoot).catch(() => null);
    if (!canonicalPackageRoot || !contained(canonicalRoot, canonicalPackageRoot)) {
      continue;
    }
    const packageJson = await fs2.realpath(path4.join(canonicalPackageRoot, "package.json")).catch(() => null);
    if (!packageJson || !contained(canonicalRoot, packageJson) || !(await fs2.stat(packageJson).catch(() => null))?.isFile()) {
      continue;
    }
    const pkg = await readJson(packageJson).catch(() => null);
    if (pkg?.name !== "npm") {
      continue;
    }
    const entry = await fs2.realpath(path4.join(canonicalPackageRoot, "bin/npm-cli.js")).catch(() => null);
    if (!entry || !contained(canonicalRoot, entry)) {
      continue;
    }
    if ((await fs2.stat(entry).catch(() => null))?.isFile()) {
      return { command: nodeExecutable, args: [entry] };
    }
  }
  throw new Error(
    `npm is missing or invalid in the selected HarmonyOS toolchain: ${toolchainRoot}`
  );
}
async function npmEnvironment(target, input = process.env) {
  const env = { ...input };
  const key = Object.keys(env).find(
    (name) => name.toLowerCase() === "npm_config_allow_scripts"
  );
  if (!key) {
    return env;
  }
  const policy = env[key];
  if (policy && /[\r\n]/.test(policy)) {
    throw new Error("npm allow-scripts policy must be a single line.");
  }
  await fs2.writeFile(
    path4.join(target, ".npmrc"),
    `allow-scripts=${JSON.stringify(policy)}
`
  );
  delete env[key];
  return env;
}
async function removeOldInstalls(root, currentId) {
  const installs = path4.join(root, "installs");
  for (const entry of await fs2.readdir(installs, { withFileTypes: true })) {
    if (entry.name === currentId || !entry.isDirectory() || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(
      entry.name
    )) {
      continue;
    }
    const oldInstall = path4.join(installs, entry.name);
    try {
      await fs2.rm(oldInstall, { recursive: true, force: true });
    } catch (error) {
      console.error(
        `Runtime updated, but could not remove old installation ${oldInstall}: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  }
}
async function installRuntime(metadata, version, pluginRoot2, dependencies = {}, context = {}) {
  if (isSemver(version)) {
    assertMinimum(metadata, version);
  }
  const inputEnv = context.env ?? process.env;
  if (process.platform === metadata.harmonyos.platform && !inputEnv.DEVECO_PLUGIN_INSTALL_ROOT) {
    const result = await installHarmonyGlobal(
      metadata,
      version,
      dependencies,
      context
    );
    if (result !== null) {
      return result;
    }
  }
  const root = path4.resolve(installRoot(metadata, inputEnv));
  if (contained(pluginRoot2, root) || contained(process.cwd(), root) || root === path4.parse(root).root) {
    throw new Error(
      "The private Runtime directory must be outside the plugin and current project directories."
    );
  }
  const npm = dependencies.npmInvocation ? await dependencies.npmInvocation() : await npmInvocation(
    inputEnv,
    context.toolchainRoot,
    context.nodeExecutable
  );
  const run = dependencies.runProcess || runProcess;
  await fs2.mkdir(root, { recursive: true });
  const stateRoot = context.toolchainRoot ? path4.join(
    inputEnv.HOME || metadata.harmonyos.homeDirectory,
    ".local/state/deveco-cli",
    metadata.taskNamespace,
    "tasks/runtime"
  ) : root;
  await fs2.mkdir(stateRoot, { recursive: true });
  const lockDirectory = context.toolchainRoot ? path4.join(
    inputEnv.HOME || metadata.harmonyos.homeDirectory,
    ".local/state/deveco-cli/locks/runtime"
  ) : root;
  await fs2.mkdir(lockDirectory, { recursive: true });
  const lockFile = path4.join(
    lockDirectory,
    context.toolchainRoot ? `${createHash("sha256").update(await fs2.realpath(root)).digest("hex")}.lock` : "install.lock"
  );
  const lock = await fs2.open(lockFile, "wx").catch((error) => {
    if (error.code !== "EEXIST") {
      throw error;
    }
    throw new Error(
      `Another installation holds ${lockFile}. If it was interrupted, confirm its process has stopped before removing this lock.`
    );
  });
  const installId = randomUUID();
  const target = path4.join(root, "installs", installId);
  const next = path4.join(root, `current-${installId}.json`);
  const installLog = context.toolchainRoot ? path4.join(stateRoot, `install-${installId}.log`) : null;
  const log = (message) => installLog === null ? Promise.resolve() : fs2.appendFile(installLog, `[${(/* @__PURE__ */ new Date()).toISOString()}] ${message}
`);
  let activated = false;
  try {
    await lock.writeFile(
      JSON.stringify({
        pid: process.pid,
        packageName: metadata.packageName,
        version
      })
    );
    await fs2.mkdir(target, { recursive: true });
    const spec = `${metadata.packageName}@${version}`;
    await log(`Runtime installation started: ${spec}`);
    await log(`Install directory: ${target}`);
    await log(`npm command: ${npm.command} ${npm.args.join(" ")}`);
    console.error(`Installing ${spec} into ${target}`);
    const env = await npmEnvironment(target, inputEnv);
    await log("Starting npm install; waiting for the npm process to exit.");
    const result = await run(
      npm.command,
      [
        ...npm.args,
        "install",
        "--prefix",
        target,
        "--no-audit",
        "--no-fund",
        "--omit=dev",
        spec
      ],
      { cwd: target, env }
    );
    await log(`npm install exited with code ${result.exitCode}.`);
    if (result.exitCode !== 0) {
      await log(`npm stderr: ${result.stderr || "(empty)"}`);
      return NPM_FAILURE;
    }
    await log("npm install completed; verifying the installed package.");
    const packageRoot = path4.join(target, "node_modules", metadata.packageName);
    const pkg = await readJson(path4.join(packageRoot, "package.json"));
    const binEntry = pkg.bin?.devecocli;
    if (pkg.name !== metadata.packageName || typeof binEntry !== "string") {
      throw new Error(
        "npm installed an unexpected package or CLI entry. The previous Runtime is unchanged."
      );
    }
    assertMinimum(metadata, pkg.version, " The previous Runtime is unchanged.");
    const entry = path4.join(packageRoot, binEntry);
    const verifyNode = context.nodeExecutable ?? process.execPath;
    const installed = await identifyRuntime(metadata, {
      command: verifyNode,
      args: [entry],
      entry,
      source: "private",
      version: pkg.version
    });
    const verify = await run(verifyNode, [entry, "--version"], {
      capture: true,
      timeout: 3e4,
      cwd: target,
      env: inputEnv
    });
    if (verify.exitCode !== 0 || verify.stdout.trim() !== await runtimeCliVersion(metadata, installed)) {
      throw new Error(
        `Runtime verification failed: ${verify.stderr || verify.stdout}. The previous Runtime is unchanged.`
      );
    }
    await fs2.writeFile(
      next,
      JSON.stringify(
        { installId, packageName: pkg.name, version: pkg.version },
        null,
        2
      ) + "\n"
    );
    await fs2.rename(next, path4.join(root, "current.json"));
    activated = true;
    await removeOldInstalls(root, installId);
    await log(`Runtime installation completed and activated: ${pkg.version}`);
    console.error(
      `Installed ${pkg.name}@${pkg.version}. A global CLI that meets the minimum version still takes priority; run devecocli-runtime-check to see the selected entry.`
    );
    return 0;
  } finally {
    await fs2.rm(next, { force: true });
    if (!activated) {
      await fs2.rm(target, { recursive: true, force: true });
    }
    await lock.close();
    await fs2.unlink(lockFile);
  }
}
async function installHarmonyGlobal(metadata, version, dependencies, context) {
  const env = context.env ?? process.env;
  const prefix = path4.join(metadata.harmonyos.homeDirectory, "npm");
  const transactionId = randomUUID();
  const staging = `${prefix}.install-${transactionId}`;
  const backup = `${prefix}.backup-${transactionId}`;
  const lockFile = `${prefix}.devecocli-install.lock`;
  let lock;
  try {
    await fs2.mkdir(path4.dirname(prefix), { recursive: true });
    lock = await fs2.open(lockFile, "wx");
  } catch (error) {
    const code = error.code;
    if (code === "EACCES" || code === "EPERM") {
      console.error(
        `Cannot write shared npm prefix ${prefix}: ${error.message}. Falling back to this application's private CLI directory.`
      );
      return null;
    }
    if (code === "EEXIST") {
      throw new Error(`Another installation holds ${lockFile}.`, {
        cause: error
      });
    }
    throw error;
  }
  try {
    const npm = dependencies.npmInvocation ? await dependencies.npmInvocation() : await npmInvocation(env, context.toolchainRoot, context.nodeExecutable);
    const run = dependencies.runProcess ?? runProcess;
    console.error(
      `Installing ${metadata.packageName}@${version} globally into ${prefix}`
    );
    const hasPrevious = Boolean(await fs2.stat(prefix).catch(() => null));
    if (hasPrevious) {
      await fs2.cp(prefix, staging, { recursive: true });
    } else {
      await fs2.mkdir(staging, { recursive: true });
    }
    const result = await run(
      npm.command,
      [
        ...npm.args,
        "install",
        "--global",
        "--prefix",
        staging,
        "--no-audit",
        "--no-fund",
        "--omit=dev",
        `${metadata.packageName}@${version}`
      ],
      { cwd: staging, env }
    );
    if (result.exitCode !== 0) {
      return NPM_FAILURE;
    }
    const packageRoot = path4.join(
      staging,
      "lib/node_modules",
      metadata.packageName
    );
    const pkg = await readJson(path4.join(packageRoot, "package.json"));
    if (pkg.name !== metadata.packageName || typeof pkg.bin?.devecocli !== "string") {
      throw new Error("npm installed an unexpected package or CLI entry.");
    }
    assertMinimum(metadata, pkg.version);
    const entry = path4.join(packageRoot, pkg.bin.devecocli);
    const node = context.nodeExecutable ?? process.execPath;
    const installed = await identifyRuntime(metadata, {
      command: node,
      args: [entry],
      entry,
      source: "host",
      version: pkg.version
    });
    const verify = await run(node, [entry, "--version"], {
      capture: true,
      timeout: 3e4,
      cwd: staging,
      env
    });
    if (verify.exitCode !== 0 || verify.stdout.trim() !== await runtimeCliVersion(metadata, installed)) {
      throw new Error(
        `Global CLI verification failed: ${verify.stderr || verify.stdout}`
      );
    }
    if (hasPrevious) {
      await fs2.rename(prefix, backup);
    }
    try {
      await fs2.rename(staging, prefix);
    } catch (error) {
      if (hasPrevious) {
        await fs2.rename(backup, prefix);
      }
      throw error;
    }
    if (hasPrevious) {
      await fs2.rm(backup, { recursive: true, force: true });
    }
    console.error(
      `Installed ${pkg.name}@${pkg.version}. Run devecocli-runtime-check to verify the global entry.`
    );
    return 0;
  } finally {
    await fs2.rm(staging, { recursive: true, force: true });
    await lock.close();
    await fs2.unlink(lockFile);
  }
}

// .plugin/runtime/main.ts
var pluginRoot = path5.resolve(
  path5.dirname(fileURLToPath2(import.meta.url)),
  ".."
);
var launcherRoot = process.env.DEVECO_PLUGIN_SCRIPT_DIR ? path5.resolve(process.env.DEVECO_PLUGIN_SCRIPT_DIR, "..") : pluginRoot;
var launcher = () => path5.join(
  launcherRoot,
  "bin",
  process.platform === "win32" ? "devecocli.cmd" : "devecocli"
);
function checkOutput(status, metadata, fields = { actions: [] }) {
  const platform = process.platform;
  const native = metadata && platform === metadata.harmonyos.platform;
  const host = fields.host;
  const report = {
    schemaVersion: 1,
    status,
    host: {
      platform,
      runtimeVariant: host?.runtimeVariant ?? (metadata ? native ? "harmonyos-native" : ["win32", "darwin", "linux"].includes(platform) ? "cross-platform" : null : null)
    },
    launcher: launcher(),
    actions: fields.actions,
    environment: {
      runtimeNode: {
        executable: process.execPath,
        version: process.versions.node
      },
      ...host?.toolchain ? {
        toolchain: {
          root: host.toolchain.root,
          source: host.toolchain.source
        }
      } : {}
    },
    ...fields.cli ? { cli: fields.cli } : {},
    ...fields.error ? { error: fields.error } : {}
  };
  console.log(JSON.stringify(report));
}
function configurationFailure(metadata, message, action, host) {
  checkOutput("configuration-error", metadata, {
    host,
    actions: [{ action }],
    error: { code: "configuration-error", message }
  });
}
async function reportMissingRuntime(metadata, host, error, env) {
  const reason = error.message;
  try {
    await npmInvocation(env, host.toolchain?.root, host.toolchain?.node);
    checkOutput("cli-install-required", metadata, {
      host,
      error: { code: "cli-install-required", message: reason },
      actions: [
        {
          action: "run",
          command: path5.join(
            launcherRoot,
            "bin",
            process.platform === "win32" ? "devecocli-install.cmd" : "devecocli-install"
          ),
          waitForCompletion: true
        },
        { action: "rerun-runtime-check" }
      ]
    });
  } catch (installerError) {
    checkOutput("installer-unavailable", metadata, {
      host,
      actions: [{ action: "report-installer-unavailable" }],
      error: {
        code: "installer-unavailable",
        message: errorMessage2(installerError)
      }
    });
  }
  return 2;
}
async function checkRuntime(metadata, args) {
  if (args.length) {
    configurationFailure(
      metadata,
      "Usage: devecocli-runtime-check",
      "run-without-arguments"
    );
    return 1;
  }
  if (Number(process.versions.node.split(".")[0]) < metadata.nodeMajorMinimum) {
    checkOutput("node-unsupported", metadata, {
      actions: [{ action: "install-supported-node" }],
      error: {
        code: "node-unsupported",
        message: `Node.js ${metadata.nodeMajorMinimum} or later is required; found ${process.versions.node}.`
      }
    });
    return 2;
  }
  let host;
  try {
    host = await resolveHostContext(metadata);
  } catch (error) {
    if (error instanceof HostContextError) {
      const failure = hostContextFailure(
        metadata,
        error.status,
        error,
        launcherRoot
      );
      checkOutput(error.status, metadata, failure.fields);
      return failure.exitCode;
    }
    configurationFailure(
      metadata,
      errorMessage2(error),
      "repair-plugin-configuration"
    );
    return 1;
  }
  try {
    if (host.runtimeVariant === "harmonyos-native") {
      const checkFailure = "\u8BF7\u68C0\u67E5\u5F53\u524D\u7CFB\u7EDF\u7248\u672C\u5E76\u66F4\u65B0\u5230\u6700\u65B0\u7248\u672C\u3002";
      const result = await runProcess(
        "param",
        ["get", "const.security.developermode.state"],
        { capture: true }
      ).catch(() => {
        throw new Error(checkFailure);
      });
      const state = result.stdout.trim();
      if (result.exitCode !== 0 || !["true", "false"].includes(state)) {
        throw new Error(checkFailure);
      }
      if (state === "false") {
        checkOutput("developer-mode-required", metadata, {
          host,
          actions: [
            { action: "enable-developer-mode" },
            { action: "rerun-runtime-check" }
          ],
          error: {
            code: "developer-mode-required",
            message: "\u5F53\u524D\u8BBE\u5907\u5C1A\u672A\u5F00\u542F\u5F00\u53D1\u8005\u6A21\u5F0F\u3002\u8BF7\u5148\u4FDD\u5B58\u5DE5\u4F5C\uFF0C\u5728\u201C\u8BBE\u7F6E\u201D\u4E2D\u641C\u7D22\u201C\u8F6F\u4EF6\u7248\u672C\u201D\u6216\u201C\u5173\u4E8E\u672C\u673A\u201D\uFF0C\u8FDE\u7EED\u70B9\u51FB\u201C\u8F6F\u4EF6\u7248\u672C\u201D7 \u6B21\uFF0C\u6309\u63D0\u793A\u786E\u8BA4\u5E76\u91CD\u542F\u7535\u8111\u3002\n\u8BE6\u7EC6\u5185\u5BB9\uFF1Ahttps://consumer.huawei.com/cn/support/content/zh-cn16050438/"
          }
        });
        return 2;
      }
    }
    const env = runtimeEnvironment(metadata, host);
    const runtime = await resolveRuntime(metadata, env);
    if (!runtime.version || !runtime.implementation) {
      throw new Error(
        "The selected CLI has no verified version or implementation specification."
      );
    }
    checkOutput("ready", metadata, {
      host,
      actions: host.runtimeVariant === "harmonyos-native" ? [
        {
          action: "ensure-hishell-environment",
          file: path5.join(metadata.harmonyos.homeDirectory, ".zshrc"),
          instructions: `MUST read this file now. Compare COMMAND_LINE_TOOL_PATH with environment.toolchain.root, the CLT Node bin PATH with the parent directory of environment.runtimeNode.executable, and the DevEco CLI bin PATH with ${path5.join(metadata.harmonyos.homeDirectory, "npm/bin")}; skip writing only when all three values match. If any value is missing or different, back up the existing file if any and add or replace only these items, creating the file if absent. Preserve existing values and unrelated contents; follow the native Runtime rules.`
        }
      ] : [],
      cli: {
        version: runtime.version,
        source: runtime.source,
        ...host.runtimeVariant === "harmonyos-native" ? {
          hishell: {
            command: runtime.command,
            args: await Promise.all(
              runtime.args.map(
                (arg) => arg === runtime.entry ? fs3.realpath(arg) : Promise.resolve(arg)
              )
            )
          }
        } : {},
        implementation: {
          kind: runtime.implementation.kind,
          skillReference: runtime.implementation.skillReference
        }
      }
    });
    return 0;
  } catch (error) {
    if (!(error instanceof RuntimeUnavailableError)) {
      configurationFailure(
        metadata,
        errorMessage2(error),
        "repair-plugin-configuration",
        host
      );
      return 1;
    }
    return reportMissingRuntime(
      metadata,
      host,
      error,
      runtimeEnvironment(metadata, host)
    );
  }
}
async function isPrivateEntry(metadata, runtime, env) {
  if (runtime.source === "private") {
    return true;
  }
  const directory = installRoot(metadata, env);
  const root = await fs3.realpath(directory).catch(() => path5.resolve(directory));
  return contained(path5.join(root, "installs"), runtime.entry);
}
async function main() {
  const [mode, ...args] = process.argv.slice(2);
  let metadata;
  let metadataRead = false;
  try {
    const bundled = await readJson(path5.join(pluginRoot, "runtime.json"));
    metadataRead = true;
    metadata = clientRuntimeMetadata(
      bundled,
      process.env.DEVECO_PLUGIN_SCRIPT_DIR || path5.join(pluginRoot, "bin"),
      process.env
    );
  } catch (error) {
    if (mode === "check") {
      configurationFailure(
        null,
        errorMessage2(error),
        metadataRead ? "repair-plugin-configuration" : "reinstall-plugin"
      );
      return 1;
    }
    throw error;
  }
  if (mode === "check") {
    return withStderrDebugLogs(() => checkRuntime(metadata, args));
  }
  if (Number(process.versions.node.split(".")[0]) < metadata.nodeMajorMinimum) {
    console.error(
      `Node.js ${metadata.nodeMajorMinimum} or later is required. The available Node.js version is ${process.versions.node}.`
    );
    return 2;
  }
  if (mode === "install" && args.length === 1 && ["--help", "-h"].includes(args[0])) {
    console.log(
      [
        INSTALL_USAGE,
        `Package: ${metadata.packageName}`,
        `Minimum version: ${metadata.minimumVersion}`,
        `Default version: ${metadata.installTag || metadata.minimumVersion}`,
        ...process.platform === metadata.harmonyos.platform ? [
          `Preferred global npm prefix: ${path5.join(metadata.harmonyos.homeDirectory, "npm")}`,
          `Private fallback: ${installRoot(metadata)}`,
          "MUST keep the installer in the foreground and read its output until it exits."
        ] : [
          `Plugin-managed directory: ${installRoot(metadata)}`,
          "Global and host-managed CLIs are never modified."
        ]
      ].join("\n")
    );
    return 0;
  }
  let host;
  try {
    host = await resolveHostContext(metadata);
  } catch (error) {
    if (!(error instanceof HostContextError)) {
      throw error;
    }
    const failure = hostContextFailure(
      metadata,
      error.status,
      error,
      launcherRoot
    );
    if (failure.exitCode !== 2 || mode !== "install") {
      throw error;
    }
    checkOutput(error.status, metadata, failure.fields);
    return 2;
  }
  const env = runtimeEnvironment(metadata, host);
  if (mode === "install") {
    return installRuntime(
      metadata,
      parseVersion(args, metadata.installTag || metadata.minimumVersion),
      pluginRoot,
      {},
      {
        env,
        toolchainRoot: host.toolchain?.root,
        nodeExecutable: host.toolchain?.node
      }
    );
  }
  if (mode !== "run") {
    throw new Error("Invalid plugin entry mode.");
  }
  const runtime = await resolveRuntime(metadata, env);
  const managed = await isPrivateEntry(metadata, runtime, env);
  const cliArgs = args[0] === "--" ? args.slice(1) : args;
  if (managed && cliArgs[0] === "update" && (cliArgs.length === 1 || cliArgs[1] === "--")) {
    throw new Error(
      "This Runtime is plugin-managed. Use devecocli-install to install the plugin default, or devecocli-install --version <version-or-tag> to update it."
    );
  }
  if (managed && cliArgs[0] === "init" && !(cliArgs.length === 2 && ["--help", "-h", "help"].includes(cliArgs[1]))) {
    throw new Error(
      "This Runtime is plugin-managed. init is disabled; the plugin already provides its Skills. Use skills add/remove to manage additional Skills in the plugin skills directory, or supply an explicit --path."
    );
  }
  const result = await runProcess(
    runtime.command,
    [...runtime.args, ...withHostAgent(cliArgs, metadata.agent)],
    { env }
  );
  return result.exitCode;
}
function withHostAgent(args, agent) {
  if (!agent || args[0] !== "skills" || !["add", "remove"].includes(args[1]) || args.length === 3 && ["--help", "-h"].includes(args[2])) {
    return args;
  }
  const separator = args.indexOf("--", 2);
  const optionEnd = separator === -1 ? args.length : separator;
  if (args.slice(2, optionEnd).some((arg) => /^--(?:agent|path)(?:=|$)/.test(arg))) {
    return args;
  }
  return [
    ...args.slice(0, optionEnd),
    "--agent",
    agent,
    ...args.slice(optionEnd)
  ];
}
try {
  process.exitCode = await main();
} catch (error) {
  if (process.argv[2] === "check") {
    configurationFailure(null, errorMessage2(error), "reinstall-plugin");
  } else {
    console.error(error instanceof Error ? error.message : String(error));
  }
  process.exitCode = 1;
}
