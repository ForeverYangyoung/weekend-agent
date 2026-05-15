# weekend-agent · API

美团黑客松 06 题：周末闲时活动规划 Agent — 后端。

## 安装

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # PowerShell
pip install -e .
```

## 启动流式 API（FastAPI + SSE）

```bash
# 开发：默认 http://127.0.0.1:8000 ，热重载
python -m weekend_agent

# 或
uvicorn weekend_agent.app:app --reload --host 0.0.0.0 --port 8000
```

### 用浏览器测试（推荐，能看到「网页」）

1. 先在一个终端里启动上面的服务（不要关窗口）。
2. 打开浏览器，地址栏输入：**`http://127.0.0.1:8000/playground`**（或 **`/`**、**`/ui`**；若误打成 **`/ground`** 也会自动跳到测试页）  
   （根路径 `/` 会自动跳到测试页。）
3. 在页面里改一句话，点 **「开始规划」**，左侧会逐条出现 trace，右侧出现最终摘要和行程卡。

> 说明：之前只有 `POST /v1/agent/stream` 接口，返回的是**数据流**，不是网页；所以光启动服务、不打开上述地址，是「没有页面」的。现在内置了单页测试界面。

**若 `/playground` 返回 `Not Found`，或 `/docs` 里没有测试页路由、且 `/health` 只有 `{"status":"ok"}`：** 说明 8000 端口上的进程**不是**当前仓库这份 `weekend_agent.app`（或文件未保存 / 未 `pip install -e .`）。请按顺序做：

1. **关掉**跑 API 的终端（Ctrl+C）。
2. 在 **`apps/api`** 下执行：`pip install -e .`。
3. 再执行：`python -m weekend_agent`。
4. 访问 **`http://127.0.0.1:8000/health`**：正确版本应含 **`playground`**、**`stream_alt`** 等字段；终端会打印 **`[weekend-agent] 浏览器流式测试: ...`**。
5. 浏览器打开 **`http://127.0.0.1:8000/playground`**（或 **`/ui`**；误打成 **`/ground`** 也会跳到测试页）。

**对照：** 若 Swagger 里**只有** `POST /agent/stream`、**没有** `POST /v1/agent/stream`，多半是**另一份工程**占用了 8000；关掉旧进程后再从本仓库启动。当前仓库里 **`/agent/stream` 与 `/v1/agent/stream` 等价**，`/docs` 会**同时列出**这两条。

### 接口

| 方法   | 路径                  | 说明                                  |
| ------ | --------------------- | ------------------------------------- |
| `GET`  | `/`                   | 跳转到浏览器测试页 `/playground`      |
| `GET`  | `/playground`         | 单页：输入 + 流式展示 trace / 结果    |
| `GET`  | `/ui`                 | 短链，同上（跳转到 `/playground`）    |
| `GET`  | `/ground`             | 常见笔误 `/ground` → 跳转到 `/playground` |
| `GET`  | `/docs`               | Swagger 文档（调非流式接口更方便）    |
| `GET`  | `/health`             | 健康检查（应含 `playground` 字段）    |
| `POST` | `/v1/agent/stream`    | 流式规划（`text/event-stream`）      |
| `POST` | `/agent/stream`       | 与上一行**完全相同**（路径别名）      |

`/v1/agent/stream` 的请求体（JSON）：

```json
{
  "user_input": "下午两个人随便逛逛",
  "force_failure": null
}
```

- `force_failure` 可选 `"玩"` / `"吃"` / `"加餐"`，与 CLI `--fail` 一致，用于演示补偿链。
- 响应每行一条 `data: {JSON}\n\n`，事件字段 `event` 的取值顺序：  
  **`start` → 多次 `state` → `final` → `done`**（异常时为 `error`）。

### 本地手动调一发

> ⚠ PowerShell 的坑：
> - `curl` 在 PowerShell 里是 `Invoke-WebRequest` 的别名，**不**支持真 curl 的 `-H/-d` 语法，直接用会报 `无法将值类型 "Headers" 转换为类型 "System.String"`。请改用下面命令。
> - 控制台默认编码是 GBK，UTF-8 的中文会显示成 `?????` 或 `��`。**先执行一次** `chcp 65001` 或在当前会话里设：
>
>   ```powershell
>   [Console]::OutputEncoding = [Text.Encoding]::UTF8
>   ```

**PowerShell（推荐 `curl.exe -N`，真正的逐行流式）：**

```powershell
curl.exe -N -X POST http://127.0.0.1:8000/v1/agent/stream `
  -H "Content-Type: application/json" `
  --data-raw '{\"user_input\":\"下午两个人随便逛逛\"}'
```

> 注意 `--data-raw` 里的 `\"` 是为了在 PowerShell 里把双引号传给 `curl.exe`。若用 cmd.exe，把外层 `'…'` 换成 `"…"`，内层用 `\"` 即可。

**PowerShell（一次性拿全部结果，不需要流式时用 `Invoke-RestMethod`）：**

```powershell
$body = @{ user_input = "下午两个人随便逛逛" } | ConvertTo-Json -Compress
Invoke-RestMethod -Uri http://127.0.0.1:8000/v1/agent/stream `
  -Method POST -ContentType "application/json" -Body $body
```

**Bash / WSL / Git Bash：**

```bash
curl -N -X POST http://127.0.0.1:8000/v1/agent/stream \
  -H "Content-Type: application/json" \
  -d '{"user_input":"下午两个人随便逛逛"}'
```

**最方便的本地调试：直接调内置流式打印脚本（带颜色 + 自动 UTF-8）：**

```powershell
python -m weekend_agent.sse_probe --input "下午两个人随便逛逛"
# 演示补偿链：
python -m weekend_agent.sse_probe --input "下午带老婆孩子出去玩" --fail 吃
```

### 浏览器 / Next.js：用 `fetch` + `ReadableStream` 读流

`EventSource` 不支持带 body 的 POST，所以用 `fetch` 手动按 `\n\n` 切：

```javascript
const res = await fetch("http://127.0.0.1:8000/v1/agent/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ user_input: "下午两个人随便逛逛" }),
});
const reader = res.body.getReader();
const dec = new TextDecoder();
let buf = "";
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buf += dec.decode(value, { stream: true });
  const parts = buf.split("\n\n");
  buf = parts.pop() ?? "";
  for (const block of parts) {
    if (!block.startsWith("data: ")) continue;
    const payload = JSON.parse(block.slice(6));
    console.log(payload.event, payload);
  }
}
```

## 跑一遍 Demo

```bash
# 默认家庭场景
python -m weekend_agent.demo

# 朋友场景
python -m weekend_agent.demo --scene friends

# 注入失败，演示补偿链（答辩核爆点）
python -m weekend_agent.demo --scene friends --fail 吃

# 自定义一句话输入
python -m weekend_agent.demo --input "下午两个人随便逛逛"
```

## 当前进度

- [x] LangGraph 状态机骨架（7 节点 + 2 条件分支）
- [x] Pydantic schemas
- [x] 全节点 stub 可运行（无 LLM key 也能跑）
- [ ] 接入真实 LLM Function Calling（Profiler / Planner / Critic）
- [ ] 11 个 Mock Tool（buy_ticket / book_table / order_flowers …）
- [x] FastAPI + SSE 流式接口（`POST /v1/agent/stream`）
- [ ] Next.js 前端

## 架构

```
START → profiler → planner → critic
                     ▲         │
                     │    ┌────┴────┐
                     │  pass    fail (iter<max)
                     │    ▼         │
                     │  dry_run     │
                     │    │         │
                     │    ▼         │
                     │  executor    │
                     │    │         │
                     │    ├ ok →  notifier → END
                     │    │
                     │    └ fail → compensator
                     │                │
                     └─── 重规划 ─────┘
```
