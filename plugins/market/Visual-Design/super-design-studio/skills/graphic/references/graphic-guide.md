# 图形生成参考指南

## SVG 最佳实践

### 图标 SVG 模板

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
     stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
     role="img" aria-label="{图标描述}">
  <title>{图标名称}</title>
  <desc>{图标用途描述}</desc>
  <!-- 路径 -->
</svg>
```

### 插画 SVG 模板

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"
     role="img" aria-label="{插画描述}">
  <title>{插画名称}</title>
  <style>
    :root {
      --primary: var(--brand-primary, #FF4D4F);
      --secondary: var(--brand-secondary, #1890FF);
    }
  </style>
  <!-- 图层分组 -->
  <g id="background">...</g>
  <g id="main-content">...</g>
  <g id="decoration">...</g>
</svg>
```

### Banner SVG/HTML 混合模板

```html
<div class="banner" style="position:relative; width:750px; height:400px; overflow:hidden;">
  <!-- 底图层 -->
  <img src="background.png" alt="" style="position:absolute; inset:0; width:100%; height:100%; object-fit:cover;" />
  <!-- SVG 叠加层 -->
  <svg viewBox="0 0 750 400" style="position:absolute; inset:0; width:100%; height:100%;">
    <text x="40" y="120" font-size="48" font-weight="bold" fill="#fff">{标题}</text>
    <text x="40" y="180" font-size="24" fill="rgba(255,255,255,0.8)">{副标题}</text>
    <rect x="40" y="280" width="160" height="48" rx="24" fill="#FF4D4F" />
    <text x="120" y="310" font-size="18" fill="#fff" text-anchor="middle">{CTA}</text>
  </svg>
</div>
```

## AI 生图 Prompt 模板

### 电商 Banner 背景
```
A {style} e-commerce banner background for {product category},
color palette: {brand colors}, {composition} layout,
{mood} atmosphere, suitable for text overlay,
aspect ratio {ratio}, high resolution
```

### 纹理/图案背景
```
Seamless {pattern type} pattern, {color scheme},
{texture description}, suitable as e-commerce card background,
tileable, {resolution}
```

### 商品场景图
```
{Product type} in {scene description},
{lighting} lighting, {style} photography style,
clean background with subtle {color} gradient,
product-focused composition, e-commerce product shot
```

## 颜色方案参考

### 电商常用配色
| 场景 | 主色 | 辅助色 | 用途 |
|---|---|---|---|
| 大促/活动 | #FF2D2D | #FFD700 | 价格突出 + 金色氛围 |
| 日常/品质 | #1A1A1A | #F5F5F5 | 简约高级感 |
| 品类/生鲜 | #00B578 | #F0FFF4 | 新鲜健康感 |
| 3C/数码 | #1890FF | #E6F7FF | 科技专业感 |
| 美妆/时尚 | #FF6B9D | #FFF0F5 | 时尚柔美 |
