#!/usr/bin/env python3
import argparse
import json
import uuid
import xml.etree.ElementTree as ET


CRS = "http://ns.adobe.com/camera-raw-settings/1.0/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
X = "adobe:ns:meta/"

ET.register_namespace("x", X)
ET.register_namespace("rdf", RDF)
ET.register_namespace("crs", CRS)


DEFAULTS = {
    "PresetType": "Normal",
    "Cluster": "",
    "SupportsAmount2": "True",
    "SupportsAmount": "True",
    "SupportsColor": "True",
    "SupportsMonochrome": "True",
    "SupportsHighDynamicRange": "True",
    "SupportsNormalDynamicRange": "True",
    "SupportsSceneReferred": "True",
    "SupportsOutputReferred": "True",
    "RequiresRGBTables": "False",
    "ShowInPresets": "True",
    "ShowInQuickActions": "False",
    "CameraModelRestriction": "",
    "Copyright": "",
    "ContactInfo": "",
    "Version": "18.3.1",
    "ProcessVersion": "15.4",
    "WhiteBalance": "Custom",
    "IncrementalTemperature": "0",
    "IncrementalTint": "0",
    "Exposure2012": "0",
    "Contrast2012": "0",
    "Highlights2012": "0",
    "Shadows2012": "0",
    "Whites2012": "0",
    "Blacks2012": "0",
    "Texture": "0",
    "Clarity2012": "0",
    "Dehaze": "0",
    "Vibrance": "0",
    "Saturation": "0",
    "ParametricShadows": "0",
    "ParametricDarks": "0",
    "ParametricLights": "0",
    "ParametricHighlights": "0",
    "ParametricShadowSplit": "25",
    "ParametricMidtoneSplit": "50",
    "ParametricHighlightSplit": "75",
    "Sharpness": "0",
    "LuminanceSmoothing": "0",
    "ColorNoiseReduction": "0",
    "SplitToningShadowHue": "0",
    "SplitToningShadowSaturation": "0",
    "SplitToningHighlightHue": "0",
    "SplitToningHighlightSaturation": "0",
    "SplitToningBalance": "0",
    "ColorGradeMidtoneHue": "0",
    "ColorGradeMidtoneSat": "0",
    "ColorGradeShadowLum": "0",
    "ColorGradeMidtoneLum": "0",
    "ColorGradeHighlightLum": "0",
    "ColorGradeBlending": "70",
    "ColorGradeGlobalHue": "0",
    "ColorGradeGlobalSat": "0",
    "ColorGradeGlobalLum": "0",
    "AutoLateralCA": "0",
    "LensProfileEnable": "0",
    "LensManualDistortionAmount": "0",
    "VignetteAmount": "0",
    "DefringePurpleAmount": "0",
    "DefringePurpleHueLo": "30",
    "DefringePurpleHueHi": "70",
    "DefringeGreenAmount": "0",
    "DefringeGreenHueLo": "40",
    "DefringeGreenHueHi": "60",
    "GrainAmount": "0",
    "PostCropVignetteAmount": "0",
    "ShadowTint": "0",
    "HDREditMode": "0",
    "ConvertToGrayscale": "False",
    "OverrideLookVignette": "False",
    "ToneCurveName2012": "Linear",
    "CameraProfile": "Default Color",
    "HasSettings": "True",
}

HSL_COLORS = ["Red", "Orange", "Yellow", "Green", "Aqua", "Blue", "Purple", "Magenta"]
CALIBRATION = ["RedHue", "RedSaturation", "GreenHue", "GreenSaturation", "BlueHue", "BlueSaturation"]


def fmt(value):
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return f"+{value}" if value > 0 else str(value)
    if isinstance(value, float):
        text = f"{value:+.2f}" if value > 0 else f"{value:.2f}"
        return text.rstrip("0").rstrip(".")
    return str(value)


def add_alt(parent, name, value=""):
    node = ET.SubElement(parent, f"{{{CRS}}}{name}")
    alt = ET.SubElement(node, f"{{{RDF}}}Alt")
    li = ET.SubElement(alt, f"{{{RDF}}}li", {"{http://www.w3.org/XML/1998/namespace}lang": "x-default"})
    li.text = value


def add_curve(parent, name, points=None):
    if not points:
        points = [[0, 0], [255, 255]]
    node = ET.SubElement(parent, f"{{{CRS}}}{name}")
    seq = ET.SubElement(node, f"{{{RDF}}}Seq")
    for x, y in points:
        ET.SubElement(seq, f"{{{RDF}}}li").text = f"{int(x)}, {int(y)}"


def main():
    parser = argparse.ArgumentParser(description="Write an Adobe Camera Raw preset XMP from JSON parameters.")
    parser.add_argument("params_json")
    parser.add_argument("output_xmp")
    args = parser.parse_args()

    params = json.load(open(args.params_json, "r", encoding="utf-8"))
    name = params.pop("Name", params.pop("name", "ACR XMP Preset"))
    short_name = params.pop("ShortName", "")
    sort_name = params.pop("SortName", "")
    group = params.pop("Group", "")
    description = params.pop("Description", "")
    curve_names = ["ToneCurvePV2012", "ToneCurvePV2012Red", "ToneCurvePV2012Green", "ToneCurvePV2012Blue"]
    curves = {key: params.pop(key, None) for key in curve_names}

    attrs = {f"{{{CRS}}}{k}": v for k, v in DEFAULTS.items()}
    attrs[f"{{{CRS}}}UUID"] = params.pop("UUID", uuid.uuid4().hex.upper())

    for color in HSL_COLORS:
        for prefix in ["HueAdjustment", "SaturationAdjustment", "LuminanceAdjustment"]:
            attrs[f"{{{CRS}}}{prefix}{color}"] = "0"
    for key in CALIBRATION:
        attrs[f"{{{CRS}}}{key}"] = "0"

    for key, value in params.items():
        attrs[f"{{{CRS}}}{key}"] = fmt(value)

    root = ET.Element(f"{{{X}}}xmpmeta", {"{adobe:ns:meta/}xmptk": "MeituHub XMP Writer 0.2.1"})
    rdf = ET.SubElement(root, f"{{{RDF}}}RDF")
    desc = ET.SubElement(rdf, f"{{{RDF}}}Description", {"{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about": "", **attrs})

    add_alt(desc, "Name", name)
    add_alt(desc, "ShortName", short_name)
    add_alt(desc, "SortName", sort_name)
    add_alt(desc, "Group", group)
    add_alt(desc, "Description", description)
    for curve in curve_names:
        add_curve(desc, curve, curves.get(curve))

    tree = ET.ElementTree(root)
    ET.indent(tree, space=" ")
    with open(args.output_xmp, "xb") as output:
        tree.write(output, encoding="utf-8", xml_declaration=False)


if __name__ == "__main__":
    main()
