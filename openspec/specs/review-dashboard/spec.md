## ADDED Requirements

### Requirement: 七维雷达图可视化
复盘看板 SHALL 使用 Recharts 渲染七维雷达图，展示 7 个维度的 0–100 评分。图表数据来源为后端返回的完整评估结果（PRD §0.3 后端完整记录结构）。

#### Scenario: 雷达图正确渲染
- **WHEN** 用户进入复盘看板，评估数据加载完成
- **THEN** Recharts 雷达图显示 7 个维度轴（analysis_ability、organization_coordination、emergency_response、interpersonal_communication、language_expression、job_matching、paralinguistic_fluency_score），各顶点值对应维度得分

---

### Requirement: 音频播放器与转写文本高亮同步
复盘看板 SHALL 提供 HTML5 `<audio>` 播放器，播放进度 MUST 与转写文本高亮同步。高亮逻辑基于 `transcript_segments` 时间戳，使用 `requestAnimationFrame` 驱动（MUST NOT 使用 `setInterval` 轮询）。当前播放时间对应的段落背景色 MUST 变为 `#FEF3C7`（Tailwind bg-amber-100），调用 `scrollIntoView({ behavior: 'smooth', block: 'center' })`，其余段落恢复白色。帧间隔 ≤ 100ms。

#### Scenario: 进度条拖动触发高亮切换
- **WHEN** 用户拖动进度条至第 30 秒
- **THEN** 包含第 30 秒（±0.5 秒容差）内容的段落背景变为 bg-amber-100，自动滚动至视口中心

#### Scenario: 自然播放高亮平滑切换
- **WHEN** 音频自然播放至下一 transcript_segment 起始时间戳
- **THEN** 高亮平滑切换，无闪烁，帧间隔 ≤ 100ms

---

### Requirement: 左右双栏对照——考生原文 vs AI 示范答案
复盘看板 SHALL 以左右双栏布局渲染对照区：左侧显示考生转写原文（含高亮批注），右侧显示 LLM 生成的 `model_ideal_answer`（官方话语体系高分示范）。

#### Scenario: 双栏对照正确渲染
- **WHEN** 用户滚动至对照区
- **THEN** 左栏为考生转写文本（带改进点批注），右栏为 model_ideal_answer 完整内容

---

### Requirement: 反模板化警告横幅
复盘看板 SHALL 根据 `anti_template_warning` 字段是否为 `null` 决定是否渲染警告横幅。字段不为 null 时 MUST 显示警告横幅，展示字段文案内容。

#### Scenario: anti_template_warning 触发警告横幅
- **WHEN** anti_template_warning 不为 null（如"检测到高频套话模式，命中 X 条黑名单词组..."）
- **THEN** 复盘看板顶部渲染警告横幅，显示字段文案

#### Scenario: anti_template_warning 为 null 不渲染
- **WHEN** anti_template_warning = null
- **THEN** 复盘看板不显示任何警告横幅

---

### Requirement: 改进建议列表展示
复盘看板 SHALL 展示 LLM 生成的 `improvement_suggestions` 列表，每条建议为独立条目。

#### Scenario: 改进建议渲染
- **WHEN** 复盘看板加载评估数据
- **THEN** improvement_suggestions 数组每条以列表条目形式展示，不折叠

---

### Requirement: 结构框架检查高亮
复盘看板 SHALL 展示 `structural_framework_check` 结果，高亮显示 `missing_elements`（红色或警告色），`present_elements` 以绿色或正常色展示。

#### Scenario: 缺失结构元素高亮
- **WHEN** structural_framework_check.missing_elements 不为空
- **THEN** 缺失元素（如"长效机制"）以明显警告色展示，存在元素以绿色展示
