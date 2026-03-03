## ADDED Requirements

### Requirement: 用户邮箱密码登录
系统 SHALL 提供 `/login` 路由，调用 `supabase.auth.signInWithPassword()` 完成身份验证。成功后将 `access_token` 存入 `sessionStorage`（MUST NOT 使用 `localStorage`，防 XSS 持久化），重定向至 `/dashboard`。

#### Scenario: 登录成功跳转
- **WHEN** 用户输入正确邮箱和密码点击登录
- **THEN** HTTP 200，access_token 写入 sessionStorage，页面重定向至 /dashboard

#### Scenario: 登录失败错误提示
- **WHEN** 用户输入错误密码点击登录
- **THEN** HTTP 400，`data-testid="login-error"` 元素出现，文案固定为"邮箱或密码错误"（不区分两种失败，防账号枚举），URL 保持 /login

#### Scenario: 防重复提交
- **WHEN** 登录请求正在进行中
- **THEN** 提交按钮处于 disabled + loading 状态，禁止二次点击

---

### Requirement: 受保护路由鉴权守卫
系统 SHALL 在每个受保护页面 mount 时校验 sessionStorage 中的 JWT 令牌。令牌过期或不存在时 MUST 立即重定向至 `/login`。FastAPI 每个受保护路由 MUST 通过 `supabase-py` 的 `auth.get_user(token)` 验证令牌，令牌有效期 3600 秒。

#### Scenario: 未登录访问受保护页面
- **WHEN** 未登录用户直接访问 /dashboard 或 /interview/*
- **THEN** 立即重定向至 /login，不渲染目标页内容

#### Scenario: 令牌过期自动踢出
- **WHEN** 用户令牌过期（超 3600 秒）后访问任意受保护路由
- **THEN** 前端检测到 401，清除 sessionStorage，重定向至 /login

---

### Requirement: 数据库行级安全隔离
数据库 `evaluations` 表 MUST 启用 Row Level Security（RLS）。查询策略：`auth.uid() = user_id`，确保每个用户只能访问自己的评估记录。

#### Scenario: 跨用户数据隔离
- **WHEN** 用户 A 查询 evaluations 表
- **THEN** 仅返回 user_id = A 的记录，其他用户记录不可见

---

### Requirement: API 提交速率限制
`/api/v1/evaluations/submit` 端点 MUST 对每个用户实施每分钟最多 3 次请求的速率限制。

#### Scenario: 超出速率限制
- **WHEN** 同一用户在 60 秒内发起第 4 次提交请求
- **THEN** 返回 HTTP 429，请求被拒绝，不进入评估流程
