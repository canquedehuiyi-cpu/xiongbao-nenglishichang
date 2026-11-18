# ACR XMP Rules

Use the user's ACR-saved preset structure as the export standard.

## Required Structure

- Store the preset name in nested `crs:Name/rdf:Alt/rdf:li`.
- Store one shared group name in nested `crs:Group/rdf:Alt/rdf:li` for all five directions.
- Use `IncrementalTemperature` and `IncrementalTint` for reusable presets.
- Use `CameraProfile="Default Color"` unless a compatible profile is deliberately required.
- Include RGB and red/green/blue tone curves.
- Include both split-toning compatibility fields and current color-grading fields.
- Give every preset a unique UUID.

Generate from JSON:

```bash
python3 scripts/write_acr_xmp.py params.json output.xmp
```

Example payload:

```json
{
  "Name": "Wedding Garden 01 Main",
  "Group": "Wedding Garden",
  "Description": "Natural skin, protected highlights, fresh controlled green.",
  "IncrementalTemperature": 1,
  "IncrementalTint": 2,
  "Exposure2012": 0.1,
  "Contrast2012": 5,
  "Highlights2012": -18,
  "Shadows2012": 10,
  "Whites2012": 5,
  "Blacks2012": -4,
  "Texture": -3,
  "Clarity2012": -2,
  "Dehaze": 0,
  "Sharpness": 35,
  "LuminanceSmoothing": 10,
  "ColorNoiseReduction": 20,
  "GrainAmount": 0,
  "PostCropVignetteAmount": 0,
  "ToneCurvePV2012": [[0, 3], [64, 61], [128, 130], [192, 198], [255, 252]],
  "ToneCurvePV2012Red": [[0, 0], [255, 255]],
  "ToneCurvePV2012Green": [[0, 0], [255, 255]],
  "ToneCurvePV2012Blue": [[0, 0], [255, 255]]
}
```

The writer accepts additional scalar ACR fields as JSON keys. Use only fields supported by the target ACR version and validate the resulting behavior in ACR when using uncommon controls.

## Complete Global Scope

Use these categories when justified:

- basic tone and white balance
- texture, clarity, and dehaze
- parametric, RGB, and channel curves
- HSL hue, saturation, and luminance
- split toning and color grading
- calibration primaries
- sharpening and noise reduction
- chromatic aberration, defringe, and lens-profile toggles
- grain and post-crop vignette
- monochrome conversion and compatible profile settings

Do not claim generic preset support for image-specific healing, crop coordinates, subject masks, face masks, or AI masks. Describe them in the parameter sheet unless a verified image-specific XMP structure is available.

## Validation

Run:

```bash
xmllint --noout output.xmp
```

Inspect names and groups:

```bash
rg -n "<crs:(Name|Group)>|<rdf:li" output.xmp
```

For a LUT-compatible variant, verify non-color effects are zero and explain that only global color and tone map into the LUT.
