# 槽命令详解

本文档扩展草图模块入口中已经登记的三种槽命令，不新增命令。

## 直口槽

`Sketch.createStraightSlot(startPnt, endPnt, radiusPnt)` 单命令生成闭合腰型槽，由两条平行直线和两端两个半圆组成，四个切点相切连接。

- `startPnt`：起点半圆的圆心；
- `endPnt`：终点半圆的圆心；
- `radiusPnt`：其到两圆心中心线的垂直距离等于半宽 `r`，在中心线方向上的位置不参与半宽计算。

派生尺寸：

- 半宽：`r`；
- 总宽：`2r`；
- 总长：`|endPnt - startPnt| + 2r`。

```javascript
Sketch.createStraightSlot(
    new Point(0, 0),
    new Point(100, 0),
    new Point(50, 10)
);
```

该例半宽为 `10`、总宽为 `20`、总长为 `120`。

本地预检必须拒绝：

- `startPnt` 与 `endPnt` 重合；
- `radiusPnt` 落在中心线上；
- 计算所得半宽为零。

## 中心点圆弧槽

`Sketch.createCenterArcSlot(centerPnt, startPnt, endPnt, radiusPnt)` 的中心线是半径为 `R` 的圆弧：

- `R = |startPnt - centerPnt|`；
- `startPnt` 与 `endPnt` 到 `centerPnt` 的距离必须一致；
- 半宽 `r = ||radiusPnt - centerPnt| - R|`；
- 外侧弧半径为 `R + r`；
- 内侧弧半径为 `R - r`。

必须满足 `0 < r < R`。以下情况必须在提交前拒绝：

- 起点与圆心重合；
- 起点和终点不在同一圆上；
- `radiusPnt` 落在中心圆弧上；
- `r >= R`。

## 三点圆弧槽

`Sketch.createThreeArcSlot(startPnt, endPnt, thirdPnt, radiusPnt)` 的参数顺序是起点、终点、弧上点、半宽参考点。中心线圆弧经过前三个点，圆心和 `R` 由三点定圆在本地求出。

必须满足：

- 三点不共线；
- `0 < r < R`；
- `r = ||radiusPnt - 圆心| - R|`。

## 弧向

圆弧槽遵循草图局部坐标系右手定则：右手拇指指向局部 `normal`，四指从 `startPnt` 转向 `endPnt` 的正向旋转方向就是弧向。三点圆弧槽还必须经过 `thirdPnt`。

## 本地预检

提交前使用执行器技能目录下的 `scripts/sketch_slot.py`。保持当前任务工作区为工作目录，将执行器技能 `SKILL.md` 所在目录的实际绝对路径加入 `sys.path` 后导入 `scripts.sketch_slot`，不切换到技能安装目录：

- `validate_center_arc_slot` 核对起点和终点等距，并返回 `R`、`r`；
- `validate_three_arc_slot` 使用 `circumcircle` 三点定圆，并返回圆心、`R`、`r`；
- 两者都必须验证 `0 < r < R`。

所有计算只在 CAD 执行前完成。最终 CrownScript 中只保留已确认命令和展开后的数值字面量。
