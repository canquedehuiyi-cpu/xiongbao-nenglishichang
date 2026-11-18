# Visual Intent To ACR

Use this reference to convert software-neutral observations into ACR controls. Treat values as starting points, not universal recipes.

## Translation Order

1. Correct technical problems first: exposure, clipping, white balance, mixed light, noise, and lens issues.
2. Shape tone: contrast, highlight roll-off, shadow depth, white and black points, then curves.
3. Shape palette: HSL, color grading, calibration, and channel curves.
4. Shape texture: texture, clarity, dehaze, sharpening, noise reduction, grain, and vignette.
5. Separate batch-safe changes from image-specific changes.

## Common Mappings

| Visual intent | Primary controls | Secondary controls | Watch for |
| --- | --- | --- | --- |
| Brighter and airy | Exposure, Whites, Shadows | Highlights, RGB curve | clipped skin and white clothing |
| Deep but not crushed shadows | Blacks, Shadows, RGB curve | Shadow color grading | lost hair and clothing detail |
| Soft highlight roll-off | Highlights, Whites, upper curve | highlight luminance | flat faces or gray whites |
| Clean white | WB, Tint, HSL Yellow/Blue | channel curves | skin becoming cyan or magenta |
| Reduce yellow skin | WB, Orange/Yellow HSL | calibration Red/Green | lifeless or gray skin |
| Reduce red skin | Tint, Red/Orange saturation | Red calibration, red curve | gray lips and cheeks |
| Fresh green | Green/Yellow hue and saturation | Green calibration | cyan skin and fluorescent foliage |
| Deep green | Green luminance and saturation | Blacks, green curve | blocked foliage |
| Cool white flash | WB, Blue/Aqua HSL | cool shadows, bright whites | blue-gray skin |
| Warm documentary | WB, Yellow/Orange HSL | warm highlights | yellow whites and orange skin |
| Film-like separation | gentle curve, HSL compression | grading, calibration | excessive fade or color cast |
| Crisp commercial | contrast, whites, texture | sharpening, noise reduction | halos and plastic skin |
| Soft portrait texture | texture reduction | local face mask suggestion | loss of eyes, hair, and fabric detail |
| Low-light cleanup | denoise, color NR, sharpening | shadows, black point | waxy detail and color smearing |

## Parameter Reasoning

For every important adjustment, connect the number to an observable goal. Example:

```text
目标：保持室内暖光，但避免肤色发橙。
转译：白平衡只轻微降温；橙色饱和度下降；橙色明亮度略升；高光保留少量暖色分级。
```

When the source image is unavailable and only a reference is provided, avoid overconfident exposure and white-balance numbers. Mark them as starting values and explain which controls need per-image adaptation.

## Reference Priority

Apply priorities in this order:

1. Explicit exclusions and safety requirements.
2. Explicit written style preference.
3. Reference image appearance.
4. Default genre convention.

If a reference depends heavily on makeup, lighting, diffusion, lens character, or local retouching, say which part cannot be recreated by global ACR controls alone.
