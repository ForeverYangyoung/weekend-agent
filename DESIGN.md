# Weekend Agent 设计文档

## 1. 架构总览

```
用户输入 → Profiler → Planner → Critic → DryRun → Executor → (Compensator) → Notifier → 前端
                ↑                    ↓          ↑                        │
                └── 重规划 ←─────────┘          └── 修订 ← 用户反馈 ←─────┘
                                                   │
                                                   ├─ Revision(解析反馈)
                                                   └─ PlanPatcher(应用补丁)
                                                         └─ build_plans(重新生成备选)
```

核心原则：**规则优先，LLM 兜底**。Profiler / Critic / Revision 全部基于关键词规则，零延迟；仅在 SummaryCard 生成时调用 LLM。

状态机基于 LangGraph，9 个节点通过 `AgentState` TypedDict 传递上下文。整个管线同步执行，mock 美团通过 ASGI 内联（零端口）或 TCP 切换。

---

## 2. Planning 策略

### 2.1 Profiler：画像提取（纯规则）

`analyze_profile()` 从用户一句话中提取结构化画像：

| 字段 | 提取方式 | 示例输入 → 输出 |
|------|---------|---------------|
| scene | 三元组关键词匹配（家庭/朋友/情侣/独自） | "带娃去公园" → family |
| people_count | 正则数字 > 短语表 > 场景默认值 | "一家三口" → 3 |
| kids_ages | 正则 `\d+岁` | "孩子5岁" → [5] |
| start_time | 正则 `下午\d点`，含时段兜底 | "下午2点" → 14:00 |
| dietary | 关键词（低卡/不辣） | "减肥" → ["低卡"] |
| interests | 关键词（亲子/户外/剧本杀） | "户外运动" → ["户外"] |
| budget | 正则 `\d+元/人` | "人均300" → 300 |

同时产出 `PlanningPreferences`（场景默认风格 + 关键词增强）和 `SearchStrategy`（品类 + 避开列表），供 Planner 使用。每个字段附带 `ProfileEvidence`（触发词 + 置信度），支持可解释性。

### 2.2 Planner：检索 → 打分 → 排序 → 校验

**检索**：通过 `search_poi(scene, stage, category)` 从 mock 美团拉取 POI 候选。场景 × 阶段 × 品类三维过滤，家庭场景自动提升"亲子"标签权重。

**五维加权打分**（`_score_one`）：

| 维度 | 权重 | 计算方式 |
|------|------|---------|
| preference | 35% | POI 标签与 profile.interests / dietary 的 Jaccard 重叠 |
| history | 20% | 与历史偏好权重的重叠（无历史则 0.5） |
| rating | 20% | POI 原始评分，截断到 [0,1] |
| distance | 15% | `1.0 - distance / limit`，超限直接过滤 |
| budget | 10% | 预算内=1.0，超出线性衰减（仅"吃"阶段） |

**硬约束过滤**：家场景必须儿童友好；低卡饮食必须轻食类；距离超限剔除。过滤后若为空则回退到原始候选。

**方案构建与多样性**：对"玩"和"吃"分别取 Top-3 候选，枚举 (顺序, play候选下标, eat候选下标, addon候选下标) 多种组合。优先级：
1. 主选：最优顺序 + 最高分 POI
2. 备选顺序 + 最优 POI
3. 备选顺序 + 换玩/换吃
4. 备选顺序 + 全换（最大化差异）

去重规则：两方案的 POI ID 集合完全相同才视为重复（允许部分重叠，确保方案之间至少有一个不同的店）。经 `validate_plan()` 校验后按总分降序返回 Top-2。

共享常量集中在 `backend/planner/constants.py`（阶段时长、中英文映射、加餐品类分组、工具映射、预算/时间容忍度等），所有模块统一引用，消除硬编码。

**兜底**：检索为零时使用场景硬编码 stub（家庭 → 奥森公园+Wagas，朋友 → 剧本杀+烤肉）。

### 2.3 Revision：用户反馈 → 局部修改

用户反馈"公园不错别动，餐厅换个日料"经 `parse_feedback_to_patches()` 解析为 `PlanPatch` 列表：

```
关键词规则优先级：reorder > replace > insert > lock > remove
目标检测：addon(品类词) > food(餐厅词) > play(玩/公园)
约束提取：否定(不要X) / 肯定(要X)
```

`revise_plan()` 按序应用补丁：先处理 lock（标记 locked_stages），再执行 replace / insert / remove / reorder。每个 mutation 检查 locked_stages，被锁定阶段跳过。全部应用后重新 validate。

**加餐路由引擎**（`backend/planner/route_insertion.py`）：品类决定插入位置 — 奶茶/咖啡/小吃插入玩→吃之间，蛋糕/甜品/花插入吃之后，绕路超过 10 分钟自动降级。

**修订后重新生成备选**：`/v1/plan/revise` 在应用修订后自动调用 `build_plans`（block 已选方案 POI），返回 `alternative_plans`（2 个不同方案）。前端同时展示修订方案 + 新备选，用户可以继续修改或选择。

每次修订产出 `PlanSnapshot`（前后版本）和 `PlanEvent` 列表（中文摘要），前端渲染为 ✓ 变更日志，支持版本回溯。

---

## 3. 工具调用链路

### 3.1 两层 HTTP 架构

```
Agent Node → invoke(tool_name, args)
              → registry.py: 查找路径 + 构建载荷
                → http_client.post_json(path, payload)
                  → httpx.AsyncClient (ASGITransport 内联，或 TCP)
                    → mock_meituan FastAPI routes
                      → MockBackend (内存)
```

`http_client.py` 支持双模切换：
- **internal**（默认）：`ASGITransport(app=mock_app)`，进程内调用，零端口
- **tcp**：设 `MOCK_MEITUAN_BASE_URL=http://host:port` 即可切真 API

所有对外函数同步（`asyncio.run` 包异步），节点代码无需感知 HTTP。

### 3.2 DryRun → Executor → Compensator

| 节点 | 工具 | 说明 |
|------|------|------|
| **DryRun** | `check_activity_availability` / `check_table_availability` / `check_addon_stock` | 只读预检，确认票位/桌位/库存可用 |
| **Executor** | `buy_ticket` / `book_table` / `order_addon` | 正式下单，带幂等键 `idempotency_key`；仅执行 DryRun 通过的调用 |
| **Compensator** | `cancel_order` | 回滚已成功的订单（Executor 部分失败时触发），成功后标记 `ROLLED_BACK`，清空调用列表并重规划 |

工具注册在 `registry.py`，`plan_mapping.py` 维护阶段→工具映射和只读→写入工具映射。

### 3.3 故障注入

Executor 支持通过请求 body 中的 `force_fail` 字段注入演示故障：
- `"玩"` → HTTP 410（门票售罄）
- `"吃"` → HTTP 409（餐厅满座）
- `"加餐"` → HTTP 409（库存不足）

Compensator 将 `force_failure` 置 `None`，确保重试路径干净。

---

## 4. 异常处理机制

### 4.1 错误传播

```
MockBackend 抛 ToolError(code, message, details)
  → routes.py: _from_tool_error() 转为 HTTPException
    → http_client.py: _ensure_ok() 4xx/5xx → 重新抛 ToolError
      → registry.py invoke() → 抛给调用节点
```

`ToolError` 携带业务语义（code 对应 HTTP 状态码，details 含具体原因），节点据此决策。

### 4.2 节点级容错

| 节点 | 策略 |
|------|------|
| Planner `_search_stage` | ToolError → 返回空列表，触发 stub 兜底 |
| DryRun | ToolError → 标记 `FAILED`，不阻塞其他调用 |
| Executor | ToolError → 加入 `failed_calls`，不中断管线 |
| Compensator | cancel 失败 → 记入 `rollback_errors`，继续回滚其余订单 |

### 4.3 补偿与重试

Executor 部分失败时：
1. Compensator 遍历 `executed_calls`，取消所有已成功订单（幂等键去重）
2. 清空 `executed_calls` 和 `dry_run_calls`，保留 `failed_calls` 作为 blocked 列表
3. `force_failure` 置 `None`，避免重试时再次触发演示故障
4. 路由回 Planner 重规划，blocked POI 自动排除

### 4.4 迭代上限与 SSE 可靠性

`config.py` 控制两级上限：
- `max_plan_iterations = 3`：Planner 重规划最大次数
- `max_revision_rounds = 5`：用户修订最大轮次

达到上限后强制进入 DryRun / Notifier，防止无限循环。

**SSE 双通道投递**：`plan` 和 `plan_alternatives` 同时在 state 事件（每次状态变更）和 final 事件（流结束）中发送。前端优先从 state 事件获取，若代理层缓冲导致丢失，final 事件作为兜底，确保方案数据不丢失。
