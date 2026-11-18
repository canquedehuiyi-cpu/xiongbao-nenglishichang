const ids = Object.freeze({
  project: "A00000000000000000000001",
  mainGroup: "A00000000000000000000002",
  sourceGroup: "A00000000000000000000003",
  productGroup: "A00000000000000000000004",
  hostProduct: "A00000000000000000000005",
  reloadProduct: "A00000000000000000000006",
  hostSource: "A00000000000000000000007",
  reloadSource: "A00000000000000000000008",
  registrySource: "A00000000000000000000009",
  configSource: "A0000000000000000000000A",
  hostSourceBuild: "A0000000000000000000000B",
  hostRegistryBuild: "A0000000000000000000000C",
  hostConfigBuild: "A0000000000000000000000D",
  reloadSourceBuild: "A0000000000000000000000E",
  reloadRegistryBuild: "A0000000000000000000000F",
  reloadConfigBuild: "A00000000000000000000010",
  hostSnapshotBuild: "A00000000000000000000011",
  hostPackageBuild: "A00000000000000000000012",
  reloadSnapshotBuild: "A00000000000000000000013",
  reloadPackageBuild: "A00000000000000000000014",
  hostTarget: "A00000000000000000000015",
  reloadTarget: "A00000000000000000000016",
  hostSources: "A00000000000000000000017",
  hostFrameworks: "A00000000000000000000018",
  hostResources: "A00000000000000000000019",
  reloadSources: "A0000000000000000000001A",
  reloadFrameworks: "A0000000000000000000001B",
  projectConfigs: "A0000000000000000000001C",
  hostConfigs: "A0000000000000000000001D",
  reloadConfigs: "A0000000000000000000001E",
  projectDebug: "A0000000000000000000001F",
  projectRelease: "A00000000000000000000020",
  hostDebug: "A00000000000000000000021",
  hostRelease: "A00000000000000000000022",
  reloadDebug: "A00000000000000000000023",
  reloadRelease: "A00000000000000000000024",
  localPackage: "A00000000000000000000025",
  snapshotPackage: "A00000000000000000000026",
  packageProduct: "A00000000000000000000027",
  snapshotProduct: "A00000000000000000000028",
});

export function generatedPreviewConfiguration(moduleName, filters) {
  const encodedFilters = filters?.length ? `[${filters.map(quote).join(", ")}]` : "nil";
  return `import ${moduleName}\n\nlet canvasPreviewModules: [String]? = [${quote(moduleName)}]\nlet canvasPreviewFilters: [String]? = ${encodedFilters}\n`;
}

export function generatedPreviewProject({
  bundleIdentifier,
  deploymentTarget,
  hostTarget,
  packageProduct,
  packageRelativePath,
  reloadTarget,
}) {
  return `// !$*UTF8*$!
{
  archiveVersion = 1;
  classes = {};
  objectVersion = 77;
  objects = {

/* Begin PBXBuildFile section */
    ${ids.hostSourceBuild} = {isa = PBXBuildFile; fileRef = ${ids.hostSource}; };
    ${ids.hostRegistryBuild} = {isa = PBXBuildFile; fileRef = ${ids.registrySource}; };
    ${ids.hostConfigBuild} = {isa = PBXBuildFile; fileRef = ${ids.configSource}; };
    ${ids.reloadSourceBuild} = {isa = PBXBuildFile; fileRef = ${ids.reloadSource}; };
    ${ids.reloadRegistryBuild} = {isa = PBXBuildFile; fileRef = ${ids.registrySource}; };
    ${ids.reloadConfigBuild} = {isa = PBXBuildFile; fileRef = ${ids.configSource}; };
    ${ids.hostSnapshotBuild} = {isa = PBXBuildFile; productRef = ${ids.snapshotProduct}; };
    ${ids.hostPackageBuild} = {isa = PBXBuildFile; productRef = ${ids.packageProduct}; };
    ${ids.reloadSnapshotBuild} = {isa = PBXBuildFile; productRef = ${ids.snapshotProduct}; };
    ${ids.reloadPackageBuild} = {isa = PBXBuildFile; productRef = ${ids.packageProduct}; };
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
    ${ids.hostProduct} = {isa = PBXFileReference; explicitFileType = wrapper.application; path = ${hostTarget}.app; sourceTree = BUILT_PRODUCTS_DIR; };
    ${ids.reloadProduct} = {isa = PBXFileReference; explicitFileType = "compiled.mach-o.dylib"; path = lib${reloadTarget}.dylib; sourceTree = BUILT_PRODUCTS_DIR; };
    ${ids.hostSource} = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = CanvasPreviewHost.swift; sourceTree = "<group>"; };
    ${ids.reloadSource} = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = CanvasPreviewReload.swift; sourceTree = "<group>"; };
    ${ids.registrySource} = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = CanvasPreviewRegistry.swift; sourceTree = "<group>"; };
    ${ids.configSource} = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = CanvasPreviewConfiguration.swift; sourceTree = "<group>"; };
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
    ${ids.hostFrameworks} = {
      isa = PBXFrameworksBuildPhase;
      buildActionMask = 2147483647;
      files = (${ids.hostSnapshotBuild}, ${ids.hostPackageBuild});
      runOnlyForDeploymentPostprocessing = 0;
    };
    ${ids.reloadFrameworks} = {
      isa = PBXFrameworksBuildPhase;
      buildActionMask = 2147483647;
      files = (${ids.reloadSnapshotBuild}, ${ids.reloadPackageBuild});
      runOnlyForDeploymentPostprocessing = 0;
    };
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
    ${ids.mainGroup} = {
      isa = PBXGroup;
      children = (${ids.sourceGroup}, ${ids.productGroup});
      sourceTree = "<group>";
    };
    ${ids.sourceGroup} = {
      isa = PBXGroup;
      children = (${ids.hostSource}, ${ids.reloadSource}, ${ids.registrySource}, ${ids.configSource});
      path = Sources;
      sourceTree = "<group>";
    };
    ${ids.productGroup} = {
      isa = PBXGroup;
      children = (${ids.hostProduct}, ${ids.reloadProduct});
      name = Products;
      sourceTree = "<group>";
    };
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
    ${ids.hostTarget} = {
      isa = PBXNativeTarget;
      buildConfigurationList = ${ids.hostConfigs};
      buildPhases = (${ids.hostSources}, ${ids.hostFrameworks}, ${ids.hostResources});
      buildRules = ();
      dependencies = ();
      name = ${hostTarget};
      packageProductDependencies = (${ids.packageProduct}, ${ids.snapshotProduct});
      productName = ${hostTarget};
      productReference = ${ids.hostProduct};
      productType = "com.apple.product-type.application";
    };
    ${ids.reloadTarget} = {
      isa = PBXNativeTarget;
      buildConfigurationList = ${ids.reloadConfigs};
      buildPhases = (${ids.reloadSources}, ${ids.reloadFrameworks});
      buildRules = ();
      dependencies = ();
      name = ${reloadTarget};
      packageProductDependencies = (${ids.packageProduct}, ${ids.snapshotProduct});
      productName = ${reloadTarget};
      productReference = ${ids.reloadProduct};
      productType = "com.apple.product-type.library.dynamic";
    };
/* End PBXNativeTarget section */

/* Begin PBXProject section */
    ${ids.project} = {
      isa = PBXProject;
      attributes = { BuildIndependentTargetsInParallel = 1; LastSwiftUpdateCheck = 2660; LastUpgradeCheck = 2660; };
      buildConfigurationList = ${ids.projectConfigs};
      developmentRegion = en;
      hasScannedForEncodings = 0;
      knownRegions = (en, Base);
      mainGroup = ${ids.mainGroup};
      packageReferences = (${ids.localPackage}, ${ids.snapshotPackage});
      preferredProjectObjectVersion = 77;
      productRefGroup = ${ids.productGroup};
      projectDirPath = "";
      projectRoot = "";
      targets = (${ids.hostTarget}, ${ids.reloadTarget});
    };
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
    ${ids.hostResources} = {isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0; };
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
    ${ids.hostSources} = {
      isa = PBXSourcesBuildPhase;
      buildActionMask = 2147483647;
      files = (${ids.hostSourceBuild}, ${ids.hostRegistryBuild}, ${ids.hostConfigBuild});
      runOnlyForDeploymentPostprocessing = 0;
    };
    ${ids.reloadSources} = {
      isa = PBXSourcesBuildPhase;
      buildActionMask = 2147483647;
      files = (${ids.reloadSourceBuild}, ${ids.reloadRegistryBuild}, ${ids.reloadConfigBuild});
      runOnlyForDeploymentPostprocessing = 0;
    };
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
    ${ids.projectDebug} = {isa = XCBuildConfiguration; buildSettings = {ALWAYS_SEARCH_USER_PATHS = NO; DEBUG_INFORMATION_FORMAT = dwarf; ENABLE_TESTABILITY = YES; IPHONEOS_DEPLOYMENT_TARGET = ${deploymentTarget}; ONLY_ACTIVE_ARCH = YES; SDKROOT = iphoneos; SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG; SWIFT_VERSION = 6.0; }; name = Debug; };
    ${ids.projectRelease} = {isa = XCBuildConfiguration; buildSettings = {ALWAYS_SEARCH_USER_PATHS = NO; IPHONEOS_DEPLOYMENT_TARGET = ${deploymentTarget}; SDKROOT = iphoneos; SWIFT_COMPILATION_MODE = wholemodule; SWIFT_VERSION = 6.0; }; name = Release; };
    ${ids.hostDebug} = {isa = XCBuildConfiguration; buildSettings = {
      CODE_SIGN_STYLE = Automatic;
      CURRENT_PROJECT_VERSION = 1;
      DEVELOPMENT_TEAM = "";
      ENABLE_PREVIEWS = NO;
      GENERATE_INFOPLIST_FILE = YES;
      INFOPLIST_KEY_CFBundleDisplayName = "Qoder SwiftUI Preview";
      INFOPLIST_KEY_LSRequiresIPhoneOS = YES;
      INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
      INFOPLIST_KEY_UILaunchScreen_Generation = YES;
      LD_RUNPATH_SEARCH_PATHS = ("$(inherited)", "@executable_path/Frameworks");
      PRODUCT_BUNDLE_IDENTIFIER = ${bundleIdentifier};
      PRODUCT_NAME = "$(TARGET_NAME)";
      SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
      SUPPORTS_MACCATALYST = NO;
      SWIFT_VERSION = 6.0;
      TARGETED_DEVICE_FAMILY = "1,2";
    }; name = Debug; };
    ${ids.hostRelease} = {isa = XCBuildConfiguration; buildSettings = {
      CODE_SIGN_STYLE = Automatic;
      CURRENT_PROJECT_VERSION = 1;
      DEVELOPMENT_TEAM = "";
      ENABLE_PREVIEWS = NO;
      GENERATE_INFOPLIST_FILE = YES;
      INFOPLIST_KEY_CFBundleDisplayName = "Qoder SwiftUI Preview";
      INFOPLIST_KEY_LSRequiresIPhoneOS = YES;
      INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
      INFOPLIST_KEY_UILaunchScreen_Generation = YES;
      LD_RUNPATH_SEARCH_PATHS = ("$(inherited)", "@executable_path/Frameworks");
      PRODUCT_BUNDLE_IDENTIFIER = ${bundleIdentifier};
      PRODUCT_NAME = "$(TARGET_NAME)";
      SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
      SUPPORTS_MACCATALYST = NO;
      SWIFT_VERSION = 6.0;
      TARGETED_DEVICE_FAMILY = "1,2";
    }; name = Release; };
    ${ids.reloadDebug} = {isa = XCBuildConfiguration; buildSettings = {CODE_SIGN_STYLE = Automatic; DEVELOPMENT_TEAM = ""; EXECUTABLE_PREFIX = lib; MACH_O_TYPE = mh_dylib; PRODUCT_NAME = "$(TARGET_NAME)"; SKIP_INSTALL = YES; SUPPORTED_PLATFORMS = "iphoneos iphonesimulator"; SUPPORTS_MACCATALYST = NO; SWIFT_VERSION = 6.0; TARGETED_DEVICE_FAMILY = "1,2"; }; name = Debug; };
    ${ids.reloadRelease} = {isa = XCBuildConfiguration; buildSettings = {CODE_SIGN_STYLE = Automatic; DEVELOPMENT_TEAM = ""; EXECUTABLE_PREFIX = lib; MACH_O_TYPE = mh_dylib; PRODUCT_NAME = "$(TARGET_NAME)"; SKIP_INSTALL = YES; SUPPORTED_PLATFORMS = "iphoneos iphonesimulator"; SUPPORTS_MACCATALYST = NO; SWIFT_VERSION = 6.0; TARGETED_DEVICE_FAMILY = "1,2"; }; name = Release; };
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
    ${ids.projectConfigs} = {isa = XCConfigurationList; buildConfigurations = (${ids.projectDebug}, ${ids.projectRelease}); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release; };
    ${ids.hostConfigs} = {isa = XCConfigurationList; buildConfigurations = (${ids.hostDebug}, ${ids.hostRelease}); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release; };
    ${ids.reloadConfigs} = {isa = XCConfigurationList; buildConfigurations = (${ids.reloadDebug}, ${ids.reloadRelease}); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release; };
/* End XCConfigurationList section */

/* Begin XCLocalSwiftPackageReference section */
    ${ids.localPackage} = {isa = XCLocalSwiftPackageReference; relativePath = ${quote(packageRelativePath)}; };
/* End XCLocalSwiftPackageReference section */

/* Begin XCRemoteSwiftPackageReference section */
    ${ids.snapshotPackage} = {isa = XCRemoteSwiftPackageReference; repositoryURL = "https://github.com/EmergeTools/SnapshotPreviews-iOS.git"; requirement = {kind = revision; revision = d42446f0439217941a4e3a2ca58a643c1ac328c4; }; };
/* End XCRemoteSwiftPackageReference section */

/* Begin XCSwiftPackageProductDependency section */
    ${ids.packageProduct} = {isa = XCSwiftPackageProductDependency; package = ${ids.localPackage}; productName = ${quote(packageProduct)}; };
    ${ids.snapshotProduct} = {isa = XCSwiftPackageProductDependency; package = ${ids.snapshotPackage}; productName = SnapshotPreviewsCore; };
/* End XCSwiftPackageProductDependency section */
  };
  rootObject = ${ids.project};
}
`;
}

function quote(value) {
  return JSON.stringify(value);
}
