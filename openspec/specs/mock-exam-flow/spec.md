## ADDED Requirements

### Requirement: 考前设备麦克风检测
系统 SHALL 在进入考场前强制执行麦克风权限检测。组件初始化时调用 `navigator.mediaDevices.getUserMedia({ audio: true })`，用 Web Audio API `AnalyserNode` 渲染实时音量波形。捕获 `NotAllowedError` 时 MUST 显示红色 inline 错误提示并锁定"进入考场"按钮，MUST NOT 使用弹窗。

#### Scenario: 麦克风权限授予
- **WHEN** 用户授予麦克风权限
- **THEN** 音量波形实时渲染，"进入考场"按钮可点击

#### Scenario: 麦克风权限拒绝
- **WHEN** 用户拒绝麦克风权限（NotAllowedError）
- **THEN** 红色 inline 错误文本显示，"进入考场"按钮保持 disabled，不弹出任何 modal

---

### Requirement: 前端五态状态机（useInterviewFlowManager）
系统 SHALL 实现 `useInterviewFlowManager` 自定义 Hook，管理面试状态机完整生命周期。状态单向流转：`IDLE` → `READING`（审题 60s）→ `RECORDING`（作答，默认 180s）→ `PROCESSING`（骨架屏）→ `REVIEW`（报告）。MUST 编写单元测试覆盖所有状态跳转，MUST NOT 存在未定义中间态。

#### Scenario: 审题阶段自动推进
- **WHEN** 页面完成首次内容绘制（FCP），题目数据加载至前端 Store
- **THEN** 题目文本立即渲染，审题倒计时从 60 秒开始，录音引擎挂起

#### Scenario: 审题倒计时归零或手动跳过
- **WHEN** 审题倒计时归零或用户点击"思考完毕，开始作答"
- **THEN** 自动调用 MediaRecorder.start()，答题倒计时显现，界面右上角出现 animate-pulse 红色录制指示灯

#### Scenario: 作答结束非最后一题
- **WHEN** 用户点击"作答结束"，当前题目非最后一题
- **THEN** 调用 MediaRecorder.stop()，合并音频 Chunks 为 Blob，状态机重置，加载下一题

#### Scenario: 作答结束最后一题
- **WHEN** 用户点击"作答结束"，当前题目为最后一题
- **THEN** POST 全部录音至 /api/v1/evaluations/submit，状态跳转 PROCESSING，展示骨架屏

---

### Requirement: 精准计时器（useInterviewTimer）
系统 SHALL 实现 `useInterviewTimer(initialSeconds, onExpireCallback)` 自定义 Hook，使用 `performance.now()` 作为计时基准，结合 `document.visibilitychange` 事件在标签页切回时校准，确保计时漂移绝对误差 ≤ 1 秒/3 分钟。剩余 60 秒时 MUST 应用 Tailwind `animate-pulse text-red-600` 样式。

#### Scenario: 正常倒计时准确性
- **WHEN** 计时器启动后持续 3 分钟
- **THEN** 实际剩余时间与预期误差 ≤ 1 秒

#### Scenario: 标签页切回后校准
- **WHEN** 用户切换至其他标签页后切回
- **THEN** 计时器基于 performance.now() 重新校准，无累积漂移

#### Scenario: 剩余 60 秒视觉告警
- **WHEN** 倒计时剩余 ≤ 60 秒
- **THEN** 倒计时文本变为红色（text-red-600）并附脉冲动效（animate-pulse）

---

### Requirement: 题库随机调度
系统 SHALL 从 6 大题型中随机抽取 3–5 题生成试卷。题库使用静态 JSON 文件或轻量 SQLite 只读加载，字段严格遵循 PRD §0.1 定义（id、question_type 枚举、content、core_keywords、time_limit_seconds）。MUST NOT 出现 §8 排除范围中的题型（选择题/填空题）。

#### Scenario: 题库调度成功
- **WHEN** 用户进入 /interview/mock
- **THEN** 从 6 大 question_type 中随机选取 3–5 题加载至前端 Store，每题包含全部必填字段

#### Scenario: question_type 枚举一致性
- **WHEN** 后端返回题目数据
- **THEN** question_type 字段值严格为：COMPREHENSIVE_ANALYSIS / PLANNING_ORGANIZATION / EMERGENCY_RESPONSE / INTERPERSONAL_RELATIONSHIPS / SELF_COGNITION / SCENARIO_SIMULATION 之一，其他值视为数据错误
