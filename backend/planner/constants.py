"""跨模块共享常量。

所有时长、阶段映射、品类分组、工具名集中在此。避免同一值散落 3+ 个文件。
"""

# ═══════════════════════════════════════════════════════════════
# 时段时长（分钟）
# ═══════════════════════════════════════════════════════════════

DURATION_PLAY = 150       # 玩
DURATION_EAT = 120        # 吃
DURATION_TRANSIT = 30     # 通勤
DURATION_ADDON = 15       # 加餐
ADDON_AFTER_EAT_OFFSET = 90  # 饭后甜点/花 相对「吃」开始的偏移

# ═══════════════════════════════════════════════════════════════
# Stage 名称映射（中英双向，全项目唯一来源）
# ═══════════════════════════════════════════════════════════════

STAGE_EN2CN = {"play": "玩", "food": "吃", "addon": "加餐"}
STAGE_CN2EN = {"玩": "play", "吃": "food", "加餐": "addon"}

# ═══════════════════════════════════════════════════════════════
# 加餐品类分组
# ═══════════════════════════════════════════════════════════════

ADDON_BETWEEN = frozenset({"奶茶", "咖啡", "小吃", "冰淇淋"})  # 玩→吃 之间
ADDON_AFTER = frozenset({"蛋糕", "甜品", "花"})                # 吃 之后

# ═══════════════════════════════════════════════════════════════
# 工具名映射（读/写/路径 一处定义）
# ═══════════════════════════════════════════════════════════════

READ_TOOL = {
    "玩": "check_activity_availability",
    "吃": "check_table_availability",
    "加餐": "check_addon_stock",
}

READ_TO_WRITE = {
    "check_activity_availability": "buy_ticket",
    "check_table_availability": "book_table",
    "check_addon_stock": "order_addon",
}

TOOL_PATH = {
    "check_activity_availability": "/availability/activity",
    "check_table_availability": "/availability/table",
    "check_addon_stock": "/availability/addon",
    "buy_ticket": "/order/buy_ticket",
    "book_table": "/order/book_table",
    "order_addon": "/order/order_addon",
    "cancel_order": "/order/cancel",
}

STAGE_FAIL = {"玩": "sold_out", "吃": "table_full", "加餐": "out_of_stock"}

# ═══════════════════════════════════════════════════════════════
# 容忍度
# ═══════════════════════════════════════════════════════════════

BUDGET_TOLERANCE = 1.3      # 预算 ±30%
DURATION_TOLERANCE = 1.15   # 时长 ±15%
MAX_DETOUR_MIN = 10.0       # 顺路最大绕路（分钟）
MIN_BUDGET_FOR_ADDON = 50   # 加餐最低人均预算
