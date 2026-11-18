# iOS Simulator Setup

## Supported Runtime

Mobile Use uses full Xcode command-line tools to discover an available
iPhone Simulator, then builds with `xcodebuild` and controls it through
`simctl`. It runs only on macOS and does not target a physical iPhone.

## Install

1. Install the full Xcode application from Apple. Command Line Tools alone are
   insufficient.
2. Open Xcode once, accept its license, and allow first-launch components to
   finish installing.
3. In **Xcode > Settings > Components**, install an iOS Simulator runtime. See
   [Downloading and installing additional Xcode components](https://developer.apple.com/documentation/xcode/downloading-and-installing-additional-xcode-components).
4. In **Window > Devices and Simulators > Simulators**, create an iPhone when
   no available one exists. See [Adding additional simulators](https://developer.apple.com/documentation/safari-developer-tools/adding-additional-simulators).
5. Install Node.js with npm and npx. The setup checker verifies all three as
   separate components and reports their absolute paths. Mobile Use uses the
   pinned `serve-sim@0.1.46`; preparing it needs registry access once, then
   reuses the npm cache. `CANVAS_SERVE_SIM_NPX` may provide an explicit
   launcher path for a managed environment.

If multiple Xcode installations exist, inspect the current selection first:

```bash
xcode-select -p
```

Changing it is a system mutation. Ask before running commands such as:

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
sudo xcodebuild -runFirstLaunch
```

## Verify Without Booting

```bash
node "/absolute/loaded-setup-mobile-use-skill/scripts/check-mobile-environment.mjs" --platform ios --strict
```

The checker runs `xcodebuild -version`, locates `simctl`, verifies Node.js,
npm, and npx independently, and reads
`xcrun simctl list devices available --json`. Listing devices does not boot
one or download `serve-sim`.

## Prepare the Interaction Runtime

After the user approves npm registry access and a write to the npm cache, run:

```bash
node "/absolute/loaded-setup-mobile-use-skill/scripts/check-mobile-environment.mjs" \
  --platform ios \
  --strict \
  --prepare-ios-interaction-runtime
```

Preparation invokes `npx --yes serve-sim@0.1.46 --version`. It succeeds only
when the exact pinned version is returned. It does not globally install the
package, start a `serve-sim` daemon, boot a Simulator, or copy a Helper app.

The JSON report includes `nodePath`, `npmPath`, `npxPath`, and
`recommendedIdeEnvironment`. If Qoder or another Electron IDE was launched
before Node.js was installed, restart the IDE after setup. The IDE process
must be able to resolve both the reported npx launcher and the Node.js runtime
used by its shebang; a terminal-only `PATH` is not proof of IDE inheritance.

The plugin intentionally contains no prebuilt Helper app and does not generate
a macOS helper executable. The Canvas Node host owns its pinned `serve-sim`
process and stops it with the Canvas. Mobile Use ships only the Swift source
templates and project generator for the iOS SwiftUI preview host and reload
dylib; the disposable project and all build products are created in the user's
writable Qoder cache by that Mac's Xcode. The interaction path is qualified
for Apple silicon (`arm64`); an Intel Mac is not considered ready.

Common fixes:

- **Developer directory points to CommandLineTools:** install full Xcode and,
  with permission, select its `Contents/Developer` directory.
- **No iOS runtime:** install one in Xcode Settings > Components.
- **No available iPhone:** create one in Devices and Simulators.
- **Node.js, npm, or npx unavailable:** install a complete Node.js distribution
  and restart the IDE so its plugin host inherits the updated `PATH`. For a
  managed launch environment, provide the reported absolute
  `CANVAS_SERVE_SIM_NPX` path. A terminal-only check is not IDE proof.
- **First interaction runtime preparation fails:** verify npm registry/network
  access for `serve-sim@0.1.46`, then rerun the approved preparation command;
  do not use `latest`, install globally, or copy a Helper app manually.
- **Project build later fails:** verify the `.xcodeproj`, runnable scheme, and
  deployment target. The viewer disables code signing; do not create signing
  identities as a setup workaround.
- **Swift package preview target is ambiguous:** export the desired regular
  target from a non-dynamic library product and set `CANVAS_IOS_PACKAGE_TARGET`.
  The first preview build also resolves the pinned preview-discovery package;
  later reloads reuse DerivedData.
