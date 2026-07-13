# Code Review Loop Agent — 项目进度清单

> 定位：一个基于 LangGraph 的自主代码开发-审查-修复闭环 Agent，配合 MCP 工具生态。
> 周期：3 周 | 主打方向：Agent 工程能力（LangGraph / MCP / 状态管理）

---

## 第 1 周：基础设施 + MCP 工具层

### 1.1 项目骨架搭建
- [+] 初始化仓库，规划目录结构（`app/`, `mcp_servers/`, `agents/`, `graph/`, `frontend/`）
- [ ] 搭建 FastAPI 项目骨架，跑通一个基础 `/health` 接口
- [ ] 配置环境变量管理（`.env` + `pydantic-settings`），DeepSeek API Key 不要硬编码
- [ ] 配置日志系统（结构化日志，后续可观测性要用）

### 1.2 DeepSeek SDK 接入
- [ ] 用 OpenAI SDK 兼容方式接入 DeepSeek（`base_url` 指向 DeepSeek）
- [ ] 跑通基础 `chat.completions.create()` 调用
- [ ] 实现 streaming 输出（`stream=True`），并验证能正确接收增量 token
- [ ] 实现 Function Calling / Tool Calling 的基础封装（统一的 tool schema 转换函数）
- [ ] 写一个最小可运行的测试脚本，验证「模型能正确调用一个假工具」

### 1.3 File MCP Server
- [ ] 设计 Tool Schema：`read_file`, `write_file`, `list_dir`（参数、返回结构、错误码要规范）
- [ ] 实现 MCP Server（用官方 MCP Python SDK 起一个本地 server）
- [ ] 加输入校验：路径不能越出项目根目录（防止 path traversal）
- [ ] 加错误处理：文件不存在、权限不足、写入失败的标准化错误返回
- [ ] 单独写测试脚本，脱离 Agent 直接调用 MCP Server 验证功能

### 1.4 Git MCP Server
- [ ] 设计 Tool Schema：`git_diff`, `git_commit`, `git_branch`, `git_checkout`
- [ ] 实现 MCP Server，封装 `git` 命令行调用（用 `subprocess` 或 `GitPython`）
- [ ] **加操作白名单**：明确禁止 `push`、禁止操作 `main` 分支（这是安全亮点，务必做）
- [ ] **加审计日志**：每次 Git 操作记录时间、操作类型、参数、结果，写入本地日志文件
- [ ] 单独测试：验证越权操作（如尝试 push）会被拦截并记录

### 第 1 周产出物 checkpoint
- [ ] DeepSeek 调用 + streaming 跑通
- [ ] 两个 MCP Server 可独立启动，可用 MCP client 手动调用验证
- [ ] Git MCP 的白名单和审计日志有实际测试记录（截图/日志留存，面试要用）

---

## 第 2 周：LangGraph 状态机核心

### 2.1 State 设计
- [ ] 定义 LangGraph State schema，至少包含：
  - `task`（原始需求）
  - `plan`（Planner 输出的任务拆分）
  - `code_diff`（当前生成的代码变更）
  - `review_result`（通过 / 不通过 + 具体问题列表）
  - `retry_count`（当前重试次数）
  - `max_retry`（重试上限，建议设为 3）
  - `status`（running / success / failed / needs_human）
  - `history`（每一轮的执行记录，便于回溯和评测）

### 2.2 Planner 节点
- [ ] 实现 Planner：把用户需求拆解为具体、可执行的子任务列表
- [ ] 明确要求模型输出**结构化 JSON**（不要让它自由发挥文本），并做解析容错

### 2.3 Code 节点
- [ ] 实现 Code Agent：根据 plan 和历史 review 意见生成/修改代码
- [ ] 接入 File MCP：真正读写文件系统
- [ ] 接入 Git MCP：每次修改后生成 diff，便于 Review 节点检查
- [ ] 处理「首次生成」和「根据 Review 意见修复」两种 prompt 路径的差异

### 2.4 Review 节点（重点，面试高频追问点）
- [ ] 设计明确的 Review 判断标准（不是让模型"感觉"，而是给出结构化 checklist：语法正确性 / 是否满足需求 / 基础安全问题）
- [ ] 要求模型输出结构化结果：`{"pass": bool, "issues": [...]}`
- [ ] 实现安全审查子项：Secret 扫描（正则匹配常见 API Key / Token 格式）、简单的 Prompt Injection 迹象检测
- [ ] 明确 pass/fail 的判定逻辑写进代码注释里，方便面试时直接翻出来讲

### 2.5 条件边与循环控制
- [ ] 实现 LangGraph 的条件边：`review_result.pass == True` → END；否则 → 回到 Code 节点
- [ ] 实现 retry_count 递增逻辑，超过 `max_retry` 后跳转到 `needs_human` 终止状态（而不是死循环）
- [ ] 测试极端情况：故意让 Review 一直不通过，验证系统会在第 3 次后正确终止，而不是无限跑下去

### 2.6 状态持久化
- [ ] 实现 State 的落盘/存储（本地 JSON 或 Redis 皆可，MVP 阶段本地文件足够）
- [ ] 验证「进程中断后，能从上次的 state 恢复继续执行」（哪怕是简单的手动重启验证）

### 2.7 SSE 流式推送
- [ ] 实现 FastAPI 的 SSE 端点，把每个节点的执行状态实时推给前端
- [ ] 推送内容至少包含：当前节点名、耗时、简要结果摘要

### 第 2 周产出物 checkpoint
- [ ] 完整跑通一次「需求输入 → Planner → Code → Review → 通过 or 触发修复循环 → 结束」全流程
- [ ] 能演示一次「Review 不通过 → 自动修复 → 再次 Review 通过」的完整循环
- [ ] 能演示一次「达到 retry 上限后优雅终止」的情况

---

## 第 3 周：评测体系 + 部署 + 文档

### 3.1 可观测性
- [ ] 每个 LangGraph 节点执行时记录：耗时、token 消耗（prompt/completion）、成功或失败
- [ ] 汇总成一个简单的执行记录表（存本地文件或 SQLite 即可，不需要上重型监控系统）

### 3.2 评测脚本（重要加分项，原方案完全没有）
- [ ] 准备 10-20 个预设小任务（难度分层：简单 CRUD / 带 bug 修复 / 稍复杂逻辑）
- [ ] 写一个批量跑测脚本，自动执行这些任务并收集结果
- [ ] 统计指标：**任务成功率**、**平均重试次数**、**平均耗时**、**平均 token 消耗**
- [ ] 把结果整理成一张表格，放进 README（这是面试时最有说服力的部分之一）

### 3.3 前端（简化版）
- [ ] 一个简单页面：输入需求 → 展示 SSE 实时日志流（不需要花哨的状态图可视化）
- [ ] 展示最终 diff 和 review 结果

### 3.4 部署
- [ ] 写 Dockerfile（app 主服务 + MCP servers）
- [ ] 写 docker-compose.yml，一键启动全部服务
- [ ] 本地验证 `docker compose up` 能完整跑通一次任务

### 3.5 文档（README）
- [ ] 系统架构图（简化版，不用画原方案那么复杂的多 Agent 图）
- [ ] LangGraph DAG 图（画出 Planner → Code → Review 的循环结构）
- [ ] MCP Tool Registry 说明（每个工具的 schema、权限边界）
- [ ] 评测结果表格
- [ ] 部署步骤
- [ ] 一段「设计取舍说明」：为什么砍掉了 Test/Doc Agent、为什么不做长期 Memory —— 这段话本身就能体现你的工程判断力，面试官会很吃这个

### 第 3 周产出物 checkpoint
- [ ] Docker Compose 一键跑通
- [ ] README 完整，包含真实评测数据（不是编的）
- [ ] 能用一分钟讲清楚整个项目的架构和三个核心亮点（见下方话术）

---

## 面试话术锚点（提前准备好，背下来）

1. **LangGraph 循环设计**："我用条件边实现了 Review 失败自动回退到 Code 节点的循环，并设置了 retry budget，超过上限会终止到 needs_human 状态而不是无限重试。"
2. **MCP 安全边界**："Git MCP Server 我加了操作白名单，禁止直接 push 和操作 main 分支，并且每次操作都有审计日志。"
3. **数据驱动的可靠性证明**："我写了一个包含 N 个任务的评测脚本，实测成功率是 X%，平均重试 Y 次，这些数据都在 README 里。"

---

## 明确不做的部分（面试被问到时如何回答）

如果面试官问「为什么没有 Test Agent / 长期记忆 / RAG」，可以直接说：
> "这些是我评估过的方向，但考虑到时间和精力有限，我选择把 Review-Code 循环和 MCP 权限边界做深、做扎实，而不是每个模块都浅尝辄止。这几个方向我有明确的后续扩展计划：[简单说一句怎么扩展]。"

这个回答本身也是加分项——展示你有产品判断力，知道取舍，而不是无脑堆功能。
