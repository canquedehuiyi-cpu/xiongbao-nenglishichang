bid-deviation-crosscheck（本地个人版）v0.1.0
================================================

一、这是什么
------------------------------------------------
一个本地确定性引擎：核验用户既有偏离表 vs 方案正文：偏离表每行声明（满足/偏离）用关键词在方案正文定位，检测相反信号（表称满足但正文否定回避/表称偏离但正文声称全满足）——当要确认偏离表与实际方案是否矛盾时使用；不生成偏离表，不下是否达标的结论
判断规则在源码中，输出稳定、可复现；
跨周期状态保存在本地 dist_template/storage/，支持"记住上一次"。

二、运行方式（源码直跑，无需安装编译产物）
------------------------------------------------
1. 需要 Python 3.10+，第三方依赖见 build/requirements.txt
2. 命令行直接运行：
   python engine/main.py tasks --scenario bid_deviation_crosscheck --json     看任务契约
   python engine/main.py run  --scenario bid_deviation_crosscheck 记录.docx   跑一次
   python engine/main.py serve --scenario bid_deviation_crosscheck --port 8765  打开本地工作台
3. 〈场景名〉 填 scenarios/ 下的目录名（如 bid_deviation_crosscheck）

三、授权
------------------------------------------------
本地个人版：无 license、无试用限制，全部特性恒开放。

四、目录说明
------------------------------------------------
  SKILL.md            宿主识别用的技能描述
  engine/             引擎源码（main.py 为入口）
  scenarios/          场景包（判断规则与模板，展示层模板在
                     scenarios/bid_deviation_crosscheck/assets/pro/templates/）
  build/              依赖清单（requirements.txt）
  dist_template/      运行根目录：output/ 产物、storage/ 运行状态、
                     web/ 本地工作台、config/ 配置

五、权限范围（详见 PERMISSIONS.txt）
------------------------------------------------
- 读写本文件夹内的文件，以及你明确指定的输入文件
- 不联网；工作台只监听本机 127.0.0.1
