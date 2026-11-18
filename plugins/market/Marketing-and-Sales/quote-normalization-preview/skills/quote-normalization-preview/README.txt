quote-normalization-preview（本地个人版）v0.1.0
================================================

一、这是什么
------------------------------------------------
一个本地确定性引擎：多家供应商格式各异的报价单归一成可比单价（拉平），并对同批报价做横向偏离标记（预审）——当要把 3~5 家文本层报价拉到同一口径比较、标出显著偏离项时使用；币种/单位/含税口径由用户声明，引擎不自行换算，不输出选商结论
判断规则在源码中，输出稳定、可复现；
跨周期状态保存在本地 dist_template/storage/，支持"记住上一次"。

二、运行方式（源码直跑，无需安装编译产物）
------------------------------------------------
1. 需要 Python 3.10+，第三方依赖见 build/requirements.txt
2. 命令行直接运行：
   python engine/main.py tasks --scenario quote_normalization_preview --json     看任务契约
   python engine/main.py run  --scenario quote_normalization_preview 记录.docx   跑一次
   python engine/main.py serve --scenario quote_normalization_preview --port 8765  打开本地工作台
3. 〈场景名〉 填 scenarios/ 下的目录名（如 quote_normalization_preview）

三、授权
------------------------------------------------
本地个人版：无 license、无试用限制，全部特性恒开放。

四、目录说明
------------------------------------------------
  SKILL.md            宿主识别用的技能描述
  engine/             引擎源码（main.py 为入口）
  scenarios/          场景包（判断规则与模板，展示层模板在
                     scenarios/quote_normalization_preview/assets/pro/templates/）
  build/              依赖清单（requirements.txt）
  dist_template/      运行根目录：output/ 产物、storage/ 运行状态、
                     web/ 本地工作台、config/ 配置

五、权限范围（详见 PERMISSIONS.txt）
------------------------------------------------
- 读写本文件夹内的文件，以及你明确指定的输入文件
- 不联网；工作台只监听本机 127.0.0.1
