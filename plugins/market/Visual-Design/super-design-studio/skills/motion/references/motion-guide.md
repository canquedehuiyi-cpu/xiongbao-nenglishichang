# 动效生成参考指南

## Galacean Effects JSON 完整结构

### 基础场景配置

```json
{
  "version": "2.0",
  "type": "ge",
  "compositions": [
    {
      "id": "comp-1",
      "name": "main",
      "duration": 3.0,
      "camera": {
        "fov": 60,
        "near": 0.1,
        "far": 1000,
        "position": [0, 0, 5]
      },
      "items": []
    }
  ],
  "textures": [],
  "bins": []
}
```

### 精灵（Sprite）Item

```json
{
  "type": "sprite",
  "id": "item-1",
  "name": "logo",
  "transform": {
    "position": [0, 0, 0],
    "scale": [1, 1, 1],
    "rotation": [0, 0, 0],
    "anchor": [0.5, 0.5]
  },
  "content": {
    "renderer": {
      "texture": { "source": "logo.png" },
      "blending": 1,
      "occlusion": false
    }
  },
  "animation": {
    "position": [
      { "time": 0, "value": [0, 2, 0], "easing": "ease-out" },
      { "time": 0.8, "value": [0, 0, 0] }
    ],
    "scale": [
      { "time": 0, "value": [0.5, 0.5, 0.5] },
      { "time": 0.5, "value": [1.1, 1.1, 1.1], "easing": "ease-out" },
      { "time": 0.7, "value": [1, 1, 1], "easing": "ease-in-out" }
    ],
    "opacity": [
      { "time": 0, "value": 0 },
      { "time": 0.3, "value": 1 }
    ]
  }
}
```

### 粒子（Particle）Item

```json
{
  "type": "particle",
  "id": "item-2",
  "name": "sparkles",
  "transform": {
    "position": [0, 0, 0]
  },
  "content": {
    "renderer": {
      "texture": { "source": "sparkle.png" }
    },
    "emitter": {
      "type": "sphere",
      "radius": 0.5,
      "rate": 50,
      "maxCount": 200
    },
    "particle": {
      "life": { "min": 0.5, "max": 1.5 },
      "speed": { "min": 0.5, "max": 2 },
      "size": { "start": 0.1, "end": 0 },
      "color": {
        "start": [1, 0.8, 0.2, 1],
        "end": [1, 0.3, 0.1, 0]
      }
    }
  }
}
```

## 缓动曲线速查

| 名称 | 用途 | CSS 等价 |
|---|---|---|
| `linear` | 匀速（避免用于位移） | `linear` |
| `ease-in` | 慢入快出（出场动效） | `ease-in` |
| `ease-out` | 快入慢停（入场动效） | `ease-out` |
| `ease-in-out` | 慢入慢停（平滑过渡） | `ease-in-out` |
| `ease-out-back` | 弹性入场（微弹效果） | `cubic-bezier(0.34, 1.56, 0.64, 1)` |
| `ease-out-elastic` | 弹簧入场（强调效果） | — |
| `ease-out-bounce` | 弹跳（趣味效果） | — |

## 动效时长参考

| 类型 | 推荐时长 | 最大时长 | 说明 |
|---|---|---|---|
| 按钮点击反馈 | 150-200ms | 300ms | 即时感，超过300ms感觉迟钝 |
| 卡片展开/折叠 | 200-350ms | 500ms | 自然展开，保持流畅 |
| 页面转场 | 300-500ms | 600ms | 超过600ms感觉卡顿 |
| 弹窗进出 | 200-300ms | 400ms | 进出成对，出场可略快 |
| 数字滚动 | 500-1000ms | 1500ms | 价格滚动，ease-out减速 |
| 开屏动效 | 2000-3000ms | 4000ms | 品牌展示，结尾留0.5s静帧 |
| 循环微动效 | 1000-3000ms | 5000ms | 首尾无缝，持续吸引注意 |
| Stagger 延迟 | 50-150ms | 200ms | 多元素依次入场的间隔 |

## prefers-reduced-motion 降级方案

```javascript
// 检测用户偏好
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (prefersReducedMotion) {
  // 降级方案：直接显示最终状态，跳过长动效
  player.loadScene(reducedMotionScene);  // 简化版场景
} else {
  player.loadScene(fullMotionScene);      // 完整动效场景
}
```

**降级原则：**
- 开屏动效 → 直接展示最终画面（淡入 0.1s）
- 微交互 → 保留状态变化，移除位移和缩放动效
- 转场 → 使用简单淡入淡出替代复杂转场
- 粒子效果 → 完全移除
