# 假后台（Mock Tools）— 小白导读

## 这是啥？

`mock_client.py` = **假装是美团的服务器**，在内存里响应「查桌位」「订票」「取消」。

`registry.py` = **总机**：节点说 tool 名字，总机转给假后台。

## 谁在用？

| 节点 | 干什么 | 调用的 Tool 类型 |
|------|--------|------------------|
| `nodes/dry_run.py` | 只打听 | `check_*` |
| `nodes/executor.py` | 真下单 | `buy_ticket` / `book_table` / `order_addon` |
| `nodes/compensator.py` | 退单 | `cancel_order` |

## 答辩怎么演示失败？

在跑图时给 state 加：`force_failure: "吃"`  
→ 「吃」阶段订位会返回 409 满座 → 走 Compensator 回滚。

## 以后接真 Mock Server

只改 `mock_client.py` 里发 HTTP 到 `:8001`，**不要改**三个节点文件。
