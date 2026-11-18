# PRD HTML 模板

完整的 HTML 产品需求文档模板结构，包含所有必需章节和样式定义。

---

## HTML 模板结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${需求名称} - 产品需求文档</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
      background: #f5f7fa;
      color: #333;
      line-height: 1.6;
    }

    /* 顶部固定栏 */
    .header {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 16px 24px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      z-index: 1000;
    }
    .header h1 { font-size: 20px; font-weight: 600; }
    .header-meta {
      display: flex;
      gap: 24px;
      margin-top: 8px;
      font-size: 13px;
      opacity: 0.9;
    }
    .header-meta span { display: flex; align-items: center; gap: 4px; }

    /* 侧边栏目录 */
    .sidebar {
      position: fixed;
      top: 80px;
      left: 0;
      width: 240px;
      height: calc(100vh - 80px);
      background: white;
      border-right: 1px solid #e5e7eb;
      overflow-y: auto;
      padding: 20px 0;
      z-index: 999;
    }
    .sidebar-section {
      padding: 8px 20px;
      font-size: 12px;
      color: #9ca3af;
      text-transform: uppercase;
      font-weight: 600;
      margin-top: 12px;
    }
    .sidebar a {
      display: block;
      padding: 10px 20px;
      color: #4b5563;
      text-decoration: none;
      font-size: 14px;
      border-left: 3px solid transparent;
      transition: all 0.2s;
    }
    .sidebar a:hover {
      background: #f9fafb;
      color: #667eea;
    }
    .sidebar a.active {
      background: #eef2ff;
      color: #667eea;
      border-left-color: #667eea;
      font-weight: 500;
    }

    /* 主内容区 */
    .main {
      margin-left: 240px;
      margin-top: 80px;
      padding: 32px 48px;
      max-width: 1200px;
    }

    /* 章节样式 */
    .section {
      background: white;
      border-radius: 12px;
      padding: 32px;
      margin-bottom: 32px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .section h2 {
      font-size: 24px;
      font-weight: 600;
      color: #1f2937;
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 2px solid #e5e7eb;
    }
    .section h3 {
      font-size: 18px;
      font-weight: 600;
      color: #374151;
      margin: 24px 0 12px 0;
    }

    /* 表格样式 */
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0;
      font-size: 14px;
    }
    th {
      background: #f9fafb;
      padding: 12px;
      text-align: left;
      font-weight: 600;
      color: #374151;
      border-bottom: 2px solid #e5e7eb;
    }
    td {
      padding: 12px;
      border-bottom: 1px solid #e5e7eb;
      color: #4b5563;
    }
    tr:hover { background: #f9fafb; }

    /* 优先级标签 */
    .priority {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }
    .priority-p0 { background: #fee2e2; color: #dc2626; }
    .priority-p1 { background: #fef3c7; color: #d97706; }
    .priority-p2 { background: #dbeafe; color: #2563eb; }

    /* 状态标签 */
    .status {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
    }
    .status-done { background: #d1fae5; color: #059669; }
    .status-progress { background: #dbeafe; color: #2563eb; }
    .status-todo { background: #f3f4f6; color: #6b7280; }

    /* 高亮框 */
    .highlight-box {
      background: #fffbeb;
      border-left: 4px solid #f59e0b;
      padding: 16px 20px;
      margin: 16px 0;
      border-radius: 6px;
    }
    .highlight-box strong { color: #d97706; }

    /* 信息框 */
    .info-box {
      background: #eef2ff;
      border-left: 4px solid #667eea;
      padding: 16px 20px;
      margin: 16px 0;
      border-radius: 6px;
    }

    /* 警告框 */
    .warning-box {
      background: #fef2f2;
      border-left: 4px solid #ef4444;
      padding: 16px 20px;
      margin: 16px 0;
      border-radius: 6px;
    }

    /* 清单样式 */
    .checklist {
      list-style: none;
      padding: 0;
    }
    .checklist li {
      padding: 10px 0;
      border-bottom: 1px solid #e5e7eb;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .checklist li:before {
      content: "☐";
      font-size: 18px;
      color: #9ca3af;
    }

    /* 流程图 */
    .flow-chart {
      display: flex;
      gap: 12px;
      align-items: center;
      margin: 20px 0;
      flex-wrap: wrap;
    }
    .flow-step {
      background: #eef2ff;
      border: 2px solid #667eea;
      border-radius: 8px;
      padding: 12px 20px;
      font-weight: 500;
      color: #4338ca;
    }
    .flow-arrow {
      font-size: 24px;
      color: #9ca3af;
    }

    /* 响应式设计 */
    @media (max-width: 768px) {
      .sidebar { display: none; }
      .main { margin-left: 0; padding: 20px; }
    }
  </style>
</head>
<body>

  <!-- 顶部固定栏 -->
  <div class="header">
    <h1>${需求名称}</h1>
    <div class="header-meta">
      <span>版本：${version}</span>
      <span>作者：${author}</span>
      <span>日期：${date}</span>
      <span>状态：${status}</span>
    </div>
  </div>

  <!-- 侧边栏目录 -->
  <div class="sidebar">
    <div class="sidebar-section">产品文档</div>
    <a href="#background" class="active">需求背景</a>
    <a href="#strategy">策略矩阵</a>
    <a href="#features">功能清单</a>
    <a href="#timeline">排期规划</a>
    <a href="#collaboration">协作流程</a>
    <a href="#risks">风险应对</a>
    <a href="#appendix">附录</a>
  </div>

  <!-- 主内容区 -->
  <div class="main">

    <!-- 1. 需求背景 -->
    <div class="section" id="background">
      <h2>需求背景</h2>
      
      <h3>问题描述</h3>
      <p>${problem_description}</p>
      
      <h3>目标用户</h3>
      <table>
        <thead>
          <tr>
            <th>用户群体</th>
            <th>规模</th>
            <th>特征</th>
            <th>核心痛点</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>${user_segment_1}</td>
            <td>${scale_1}</td>
            <td>${features_1}</td>
            <td>${pain_points_1}</td>
          </tr>
        </tbody>
      </table>

      <h3>成功指标</h3>
      <div class="highlight-box">
        <p><strong>核心指标：</strong>${core_metric}</p>
        <p><strong>目标值：</strong>${target_value}</p>
        <p><strong>数据来源：</strong>${data_source}</p>
        <p><strong>达成时间：</strong>${deadline}</p>
      </div>

      <h3>约束条件</h3>
      <ul>
        <li><strong>时间约束：</strong>${time_constraint}</li>
        <li><strong>资源约束：</strong>${resource_constraint}</li>
        <li><strong>技术约束：</strong>${tech_constraint}</li>
        <li><strong>合规约束：</strong>${compliance_constraint}</li>
      </ul>
    </div>

    <!-- 2. 策略矩阵 -->
    <div class="section" id="strategy">
      <h2>策略矩阵</h2>
      
      <p>针对不同用户群体的差异化策略：</p>
      
      <table>
        <thead>
          <tr>
            <th>用户分群</th>
            <th>分群特征</th>
            <th>策略手段</th>
            <th>预期效果</th>
            <th>实施难度</th>
            <th>优先级</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>${segment_name}</td>
            <td>${segment_features}</td>
            <td>${strategy}</td>
            <td>${expected_effect}</td>
            <td>${difficulty}</td>
            <td><span class="priority priority-p0">${priority}</span></td>
          </tr>
        </tbody>
      </table>

      <div class="info-box">
        <strong>策略设计原则：</strong>
        <ul style="margin: 8px 0 0 20px;">
          <li>每个分群必须有明确的量化特征</li>
          <li>预期效果必须量化，有数据支撑</li>
          <li>策略手段必须具体可执行</li>
        </ul>
      </div>
    </div>

    <!-- 3. 功能清单 -->
    <div class="section" id="features">
      <h2>功能清单</h2>

      <div style="margin-bottom: 16px;">
        <button onclick="filterFeatures('all')" style="padding: 8px 16px; margin-right: 8px; border: 1px solid #e5e7eb; background: white; border-radius: 6px; cursor: pointer;">全部</button>
        <button onclick="filterFeatures('p0')" style="padding: 8px 16px; margin-right: 8px; border: 1px solid #e5e7eb; background: white; border-radius: 6px; cursor: pointer;">P0</button>
        <button onclick="filterFeatures('p1')" style="padding: 8px 16px; margin-right: 8px; border: 1px solid #e5e7eb; background: white; border-radius: 6px; cursor: pointer;">P1</button>
        <button onclick="filterFeatures('p2')" style="padding: 8px 16px; border: 1px solid #e5e7eb; background: white; border-radius: 6px; cursor: pointer;">P2</button>
      </div>

      <table id="featureTable">
        <thead>
          <tr>
            <th>#</th>
            <th>功能名称</th>
            <th>优先级</th>
            <th>功能描述</th>
            <th>验收标准</th>
            <th>预估工时</th>
            <th>负责人</th>
          </tr>
        </thead>
        <tbody>
          <tr data-priority="p0">
            <td>1</td>
            <td>${feature_name}</td>
            <td><span class="priority priority-p0">P0</span></td>
            <td>${feature_desc}</td>
            <td>${acceptance_criteria}</td>
            <td>${estimated_hours}</td>
            <td>${owner}</td>
          </tr>
        </tbody>
      </table>

      <div class="warning-box">
        <strong>注意：</strong>P0 功能占比不超过 30%，否则说明优先级未真正区分。
      </div>
    </div>

    <!-- 4. 排期规划 -->
    <div class="section" id="timeline">
      <h2>排期规划</h2>

      <h3>迭代概览</h3>
      <table>
        <thead>
          <tr>
            <th>迭代</th>
            <th>周期</th>
            <th>功能点</th>
            <th>优先级</th>
            <th>负责人</th>
            <th>预估工时</th>
            <th>交付日期</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Sprint 1</td>
            <td>${sprint_1_period}</td>
            <td>${sprint_1_features}</td>
            <td><span class="priority priority-p0">P0</span></td>
            <td>${sprint_1_owner}</td>
            <td>${sprint_1_hours}</td>
            <td>${sprint_1_deadline}</td>
          </tr>
        </tbody>
      </table>

      <h3>关键里程碑</h3>
      <div class="flow-chart">
        <div class="flow-step">需求评审<br><small>${review_date}</small></div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">开发完成<br><small>${dev_complete_date}</small></div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">测试完成<br><small>${test_complete_date}</small></div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">上线发布<br><small>${release_date}</small></div>
      </div>

      <div class="info-box">
        <strong>排期原则：</strong>
        <ul style="margin: 8px 0 0 20px;">
          <li>单个迭代总工时不超过可用资源的 80%（预留 20% 缓冲）</li>
          <li>P0 功能必须在迭代前半段完成</li>
          <li>联调和测试时间必须单独列出</li>
        </ul>
      </div>
    </div>

    <!-- 5. 协作流程 -->
    <div class="section" id="collaboration">
      <h2>协作流程</h2>

      <h3>需求评审流程</h3>
      <div class="flow-chart">
        <div class="flow-step">PRD 提前 2 天发出</div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">评审会议</div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">整理纪要</div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">更新 PRD</div>
      </div>

      <h3>需求变更管理</h3>
      <table>
        <thead>
          <tr>
            <th>变更类型</th>
            <th>审批人</th>
            <th>通知对象</th>
            <th>通知方式</th>
            <th>通知时限</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>细节调整</td>
            <td>产品负责人</td>
            <td>研发、测试</td>
            <td>项目群 @相关人</td>
            <td>4 小时内</td>
          </tr>
          <tr>
            <td>排期调整</td>
            <td>产品负责人</td>
            <td>研发、测试、运营、<strong>+1 直属上级</strong></td>
            <td>项目群 @all + 邮件</td>
            <td>2 小时内</td>
          </tr>
          <tr>
            <td>功能范围变更</td>
            <td>产品总监</td>
            <td>所有评审人、<strong>+1 直属上级</strong>、业务方</td>
            <td>项目群 @all + 邮件 + 更新 PRD</td>
            <td>1 小时内</td>
          </tr>
        </tbody>
      </table>

      <div class="warning-box">
        <strong>极其重要：</strong>
        <ul style="margin: 8px 0 0 20px;">
          <li>任何排期调整必须通知到 +1（直属上级）</li>
          <li>功能范围变更必须同步更新 PRD 文档</li>
          <li>通知必须说明影响和原因，不能只说"变更了"</li>
        </ul>
      </div>

      <h3>上线前检查清单</h3>
      <ul class="checklist">
        <li>研发完成自测，提交测试</li>
        <li>测试完成回归测试，输出测试报告</li>
        <li>产品完成验收测试，确认功能符合预期</li>
        <li>运营准备上线公告和用户引导材料</li>
        <li>确认上线时间和灰度策略</li>
        <li>确认回滚方案和应急预案</li>
        <li>确认数据监控指标和报警阈值</li>
        <li>通知所有相关人上线时间</li>
      </ul>
    </div>

    <!-- 6. 风险应对 -->
    <div class="section" id="risks">
      <h2>风险与应对</h2>

      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>风险描述</th>
            <th>风险类型</th>
            <th>风险等级</th>
            <th>影响范围</th>
            <th>应对策略</th>
            <th>负责人</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            <td>${risk_description}</td>
            <td>${risk_type}</td>
            <td><span class="priority priority-p0">${risk_level}</span></td>
            <td>${risk_impact}</td>
            <td>${mitigation_strategy}</td>
            <td>${risk_owner}</td>
          </tr>
        </tbody>
      </table>

      <div class="info-box">
        <strong>风险识别要点：</strong>
        <ul style="margin: 8px 0 0 20px;">
          <li>风险识别要全面：技术、业务、运营、合规</li>
          <li>高风险必须有应急预案</li>
          <li>每个风险必须有明确的负责人</li>
        </ul>
      </div>
    </div>

    <!-- 7. 附录 -->
    <div class="section" id="appendix">
      <h2>附录</h2>

      <h3>术语表</h3>
      <table>
        <thead>
          <tr>
            <th>术语</th>
            <th>定义</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>${term}</td>
            <td>${definition}</td>
          </tr>
        </tbody>
      </table>

      <h3>参考文档</h3>
      <ul>
        <li><a href="${ref_link_1}">${ref_title_1}</a></li>
        <li><a href="${ref_link_2}">${ref_title_2}</a></li>
      </ul>

      <h3>变更记录</h3>
      <table>
        <thead>
          <tr>
            <th>版本</th>
            <th>日期</th>
            <th>变更内容</th>
            <th>变更人</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>${version}</td>
            <td>${change_date}</td>
            <td>${change_desc}</td>
            <td>${change_author}</td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>

  <script>
    // 目录高亮
    const sections = document.querySelectorAll('.section');
    const navLinks = document.querySelectorAll('.sidebar a');

    window.addEventListener('scroll', () => {
      let current = '';
      sections.forEach(section => {
        const sectionTop = section.offsetTop;
        if (window.scrollY >= sectionTop - 100) {
          current = section.getAttribute('id');
        }
      });

      navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === '#' + current) {
          link.classList.add('active');
        }
      });
    });

    // 功能筛选
    function filterFeatures(priority) {
      const rows = document.querySelectorAll('#featureTable tbody tr');
      rows.forEach(row => {
        if (priority === 'all') {
          row.style.display = '';
        } else {
          const rowPriority = row.getAttribute('data-priority');
          row.style.display = rowPriority === priority ? '' : 'none';
        }
      });
    }
  </script>

</body>
</html>
```

---

## 模板使用说明

### 变量替换规则

所有 `${variable_name}` 占位符需要在生成文档时替换为实际内容：

| 变量类别 | 变量示例 | 说明 |
|---------|---------|------|
| 文档元信息 | `${需求名称}`, `${version}`, `${author}`, `${date}`, `${status}` | 文档头部信息 |
| 需求背景 | `${problem_description}`, `${user_segment_1}`, `${core_metric}` | 需求背景和成功指标 |
| 策略矩阵 | `${segment_name}`, `${strategy}`, `${expected_effect}` | 用户分群和策略设计 |
| 功能清单 | `${feature_name}`, `${acceptance_criteria}`, `${owner}` | 功能点和验收标准 |
| 排期规划 | `${sprint_1_period}`, `${release_date}` | 迭代周期和里程碑 |
| 风险应对 | `${risk_description}`, `${mitigation_strategy}` | 风险识别和应对策略 |

### 章节完整性检查

生成文档后，必须确认以下九个章节全部存在：

- [ ] 文档头部（header）
- [ ] 目录导航（sidebar）
- [ ] 需求背景（#background）
- [ ] 策略矩阵（#strategy）
- [ ] 功能清单（#features）
- [ ] 排期规划（#timeline）
- [ ] 协作流程（#collaboration）
- [ ] 风险应对（#risks）
- [ ] 附录（#appendix）

### 交互功能验证

HTML 文档包含以下交互功能，生成后需要验证：

1. **目录高亮**：滚动页面时，当前章节在侧边栏中高亮显示
2. **功能筛选**：点击 P0/P1/P2 按钮，表格只显示对应优先级的功能
3. **响应式布局**：移动端自动隐藏侧边栏，主内容区占满宽度

---

## 不同需求类型的模板调整

### 新功能需求（完整版）

使用完整模板，所有章节必须详细填写。

### 功能优化需求（精简版）

可以简化以下章节：
- 需求背景：重点描述现有问题和数据表现
- 策略矩阵：聚焦优化方案对比
- 功能清单：只列出变更点，不需要完整功能列表
- 排期规划：通常 1-2 个迭代

### Bug 修复需求（极简版）

可以省略以下章节：
- 策略矩阵：不需要
- 附录：可以省略

必须保留的章节：
- 需求背景：问题描述和复现步骤
- 功能清单：修复方案和验证标准
- 排期规划：紧急排期
- 协作流程：通知机制
