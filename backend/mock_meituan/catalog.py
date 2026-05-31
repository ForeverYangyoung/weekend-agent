"""Mock 美团：POI 目录数据。

数据布局：
  CATALOG[scene][stage] -> list[dict]，每个 dict 字段对齐 POICandidate：
    poi_id / name / category / score / reason / metadata{avg_price, distance_km, tags}

标签字段 metadata.tags 用于约束匹配（如 "不要火锅" 排除 tags 含 火锅 的 POI）。
"""

from __future__ import annotations

from typing import Any

CATALOG: dict[str, dict[str, list[dict[str, Any]]]] = {
    # ═══════════════════════════════════════════════════════════════
    # family — 亲子家庭
    # ═══════════════════════════════════════════════════════════════
    "family": {
        "玩": [
            {
                "poi_id": "poi_park_001",
                "name": "奥林匹克森林公园",
                "category": "亲子活动",
                "score": 0.92,
                "reason": "离家 6km，有儿童游乐区，5 岁孩子合适",
                "metadata": {"avg_price": 0, "distance_km": 6, "tags": ["户外", "公园", "免费", "亲子"]},
            },
            {
                "poi_id": "poi_park_002",
                "name": "朝阳公园童趣园",
                "category": "亲子活动",
                "score": 0.85,
                "reason": "距离稍远但游乐设施更丰富",
                "metadata": {"avg_price": 50, "distance_km": 9, "tags": ["户外", "公园", "游乐场", "亲子"]},
            },
            {
                "poi_id": "poi_park_003",
                "name": "海洋馆儿童区",
                "category": "亲子活动",
                "score": 0.80,
                "reason": "室内场地避免户外天气影响",
                "metadata": {"avg_price": 120, "distance_km": 8, "tags": ["室内", "海洋馆", "亲子", "教育"]},
            },
            {
                "poi_id": "poi_kid_004",
                "name": "奈尔宝家庭中心",
                "category": "儿童乐园",
                "score": 0.87,
                "reason": "室内大型儿童乐园，适合 3-10 岁",
                "metadata": {"avg_price": 180, "distance_km": 5, "tags": ["室内", "儿童乐园", "安全"]},
            },
            {
                "poi_id": "poi_kid_005",
                "name": "中国科技馆儿童厅",
                "category": "儿童科学馆",
                "score": 0.78,
                "reason": "动手体验多，寓教于乐",
                "metadata": {"avg_price": 30, "distance_km": 10, "tags": ["室内", "教育", "亲子", "动手"]},
            },
        ],
        "吃": [
            {
                "poi_id": "poi_rest_021",
                "name": "Wagas 沙拉轻食（奥森店）",
                "category": "轻食",
                "score": 0.88,
                "reason": "低卡符合减肥需求；有儿童椅",
                "metadata": {"avg_price": 80, "distance_km": 1, "tags": ["轻食", "低卡", "健康", "亲子友好"]},
            },
            {
                "poi_id": "poi_rest_022",
                "name": "绿茶餐厅",
                "category": "江浙菜",
                "score": 0.78,
                "reason": "清淡选择多，儿童套餐",
                "metadata": {"avg_price": 90, "distance_km": 2, "tags": ["清淡", "江浙菜", "亲子友好", "性价比"]},
            },
            {
                "poi_id": "poi_rest_023",
                "name": "新元素轻食",
                "category": "轻食",
                "score": 0.75,
                "reason": "低卡套餐，有机食材",
                "metadata": {"avg_price": 110, "distance_km": 3, "tags": ["轻食", "低卡", "健康", "有机"]},
            },
            {
                "poi_id": "poi_rest_024",
                "name": "海底捞火锅（望京店）",
                "category": "火锅",
                "score": 0.85,
                "reason": "服务好有儿童乐园，送小玩具",
                "metadata": {"avg_price": 150, "distance_km": 4, "tags": ["火锅", "亲子友好", "服务好"]},
            },
            {
                "poi_id": "poi_rest_025",
                "name": "味千拉面（亲子套餐）",
                "category": "日式简餐",
                "score": 0.72,
                "reason": "出餐快，孩子喜欢，价格实惠",
                "metadata": {"avg_price": 55, "distance_km": 2, "tags": ["日式", "快速", "性价比", "亲子友好"]},
            },
        ],
        "加餐": [
            {
                "poi_id": "poi_cake_007",
                "name": "原麦山丘 小蛋糕（送至餐厅）",
                "category": "蛋糕",
                "score": 0.81,
                "reason": "低糖款，给孩子的小惊喜",
                "metadata": {"avg_price": 35, "distance_km": 0, "tags": ["蛋糕", "低糖", "甜点"]},
            },
            {
                "poi_id": "poi_tea_001",
                "name": "喜茶（奥森店）",
                "category": "奶茶",
                "score": 0.78,
                "reason": "顺路买杯奶茶，孩子爱喝果茶",
                "metadata": {"avg_price": 25, "distance_km": 1, "tags": ["奶茶", "饮品", "果茶"]},
            },
            {
                "poi_id": "poi_coffee_004",
                "name": "Tims 咖啡（商场B1）",
                "category": "咖啡",
                "score": 0.68,
                "reason": "大人喝咖啡，孩子吃甜甜圈",
                "metadata": {"avg_price": 22, "distance_km": 0, "tags": ["咖啡", "饮品", "贝果"]},
            },
            {
                "poi_id": "poi_ice_001",
                "name": "DQ 冰淇淋（商场店）",
                "category": "冰淇淋",
                "score": 0.70,
                "reason": "吃完饭来杯倒杯不洒",
                "metadata": {"avg_price": 28, "distance_km": 2, "tags": ["冰淇淋", "甜点", "冰品"]},
            },
            {
                "poi_id": "poi_photo_001",
                "name": "家庭合照亭（商场B1）",
                "category": "拍照",
                "score": 0.65,
                "reason": "拍张全家福留念",
                "metadata": {"avg_price": 0, "distance_km": 0, "tags": ["拍照", "纪念"]},
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # friends — 朋友聚会
    # ═══════════════════════════════════════════════════════════════
    "friends": {
        "玩": [
            {
                "poi_id": "poi_act_101",
                "name": "罪有引力剧本杀（三里屯店）",
                "category": "剧本杀",
                "score": 0.90,
                "reason": "4 人本，2 男 2 女均衡",
                "metadata": {"avg_price": 120, "distance_km": 5, "tags": ["剧本杀", "室内", "社交", "沉浸"]},
            },
            {
                "poi_id": "poi_act_102",
                "name": "开心麻花密室逃脱",
                "category": "密室",
                "score": 0.83,
                "reason": "评价高，适合 3-6 人组团",
                "metadata": {"avg_price": 140, "distance_km": 6, "tags": ["密室", "室内", "社交", "团队"]},
            },
            {
                "poi_id": "poi_act_103",
                "name": "798 艺术区展览",
                "category": "展览",
                "score": 0.76,
                "reason": "当代艺术展，好逛好拍照",
                "metadata": {"avg_price": 60, "distance_km": 8, "tags": ["展览", "拍照", "户外", "文化"]},
            },
            {
                "poi_id": "poi_act_104",
                "name": "朝阳大悦城 KTV",
                "category": "KTV",
                "score": 0.80,
                "reason": "包厢大，曲库全，朋友聚会首选",
                "metadata": {"avg_price": 80, "distance_km": 3, "tags": ["KTV", "室内", "社交", "唱歌"]},
            },
        ],
        "吃": [
            {
                "poi_id": "poi_rest_201",
                "name": "姜虎东白丁烤肉（三里屯）",
                "category": "烤肉",
                "score": 0.89,
                "reason": "4 人聚餐口碑高，氛围热闹",
                "metadata": {"avg_price": 160, "distance_km": 1, "tags": ["烤肉", "韩式", "社交", "热闹"]},
            },
            {
                "poi_id": "poi_rest_202",
                "name": "炙烤大叔",
                "category": "烤肉",
                "score": 0.82,
                "reason": "人均稍低，无需排队",
                "metadata": {"avg_price": 110, "distance_km": 2, "tags": ["烤肉", "性价比", "自助"]},
            },
            {
                "poi_id": "poi_rest_203",
                "name": "小龙坎火锅（工体店）",
                "category": "火锅",
                "score": 0.86,
                "reason": "麻辣够味，朋友聚会涮起来",
                "metadata": {"avg_price": 140, "distance_km": 3, "tags": ["火锅", "麻辣", "社交", "热闹"]},
            },
            {
                "poi_id": "poi_rest_204",
                "name": "鸟屯日式烧鸟",
                "category": "日料",
                "score": 0.79,
                "reason": "串烧配啤酒，氛围轻松",
                "metadata": {"avg_price": 130, "distance_km": 4, "tags": ["日料", "烧鸟", "轻松", "居酒屋"]},
            },
        ],
        "加餐": [
            {
                "poi_id": "poi_flower_009",
                "name": "花点时间 小花束（送至餐厅）",
                "category": "花",
                "score": 0.76,
                "reason": "给女生的小惊喜",
                "metadata": {"avg_price": 80, "distance_km": 0, "tags": ["花", "礼物", "仪式感"]},
            },
            {
                "poi_id": "poi_tea_002",
                "name": "奈雪的茶（三里屯店）",
                "category": "奶茶",
                "score": 0.75,
                "reason": "霸气草莓来一杯，顺路带走",
                "metadata": {"avg_price": 28, "distance_km": 1, "tags": ["奶茶", "饮品", "果茶"]},
            },
            {
                "poi_id": "poi_coffee_001",
                "name": "Manner Coffee（工体店）",
                "category": "咖啡",
                "score": 0.77,
                "reason": "自带杯减 5 元，咖啡续命",
                "metadata": {"avg_price": 22, "distance_km": 2, "tags": ["咖啡", "饮品"]},
            },
            {
                "poi_id": "poi_snack_001",
                "name": "文和友小吃摊",
                "category": "小吃",
                "score": 0.68,
                "reason": "路过随手买，臭豆腐/烤串",
                "metadata": {"avg_price": 30, "distance_km": 0, "tags": ["小吃", "街头", "零食"]},
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # couple — 情侣约会
    # ═══════════════════════════════════════════════════════════════
    "couple": {
        "玩": [
            {
                "poi_id": "poi_cpl_001",
                "name": "今日美术馆",
                "category": "展览",
                "score": 0.85,
                "reason": "当代艺术展，适合安静独处，出片率高",
                "metadata": {"avg_price": 80, "distance_km": 5, "tags": ["展览", "安静", "拍照", "文化"]},
            },
            {
                "poi_id": "poi_cpl_002",
                "name": "798 艺术区画廊",
                "category": "展览",
                "score": 0.82,
                "reason": "逛画廊不花钱，拍照好看",
                "metadata": {"avg_price": 0, "distance_km": 8, "tags": ["展览", "免费", "拍照", "citywalk"]},
            },
            {
                "poi_id": "poi_cpl_003",
                "name": "双人陶艺体验馆",
                "category": "手工",
                "score": 0.88,
                "reason": "一起做陶艺，仪式感满满，成品可带走",
                "metadata": {"avg_price": 200, "distance_km": 4, "tags": ["手工", "室内", "仪式感", "互动"]},
            },
            {
                "poi_id": "poi_cpl_004",
                "name": "私享影厅（双人包间）",
                "category": "影院",
                "score": 0.78,
                "reason": "私密包间看电影，氛围感十足",
                "metadata": {"avg_price": 150, "distance_km": 3, "tags": ["室内", "私密", "电影", "氛围感"]},
            },
        ],
        "吃": [
            {
                "poi_id": "poi_rest_301",
                "name": "福楼法餐厅",
                "category": "法餐",
                "score": 0.90,
                "reason": "烛光晚餐，私密包间，约会圣地",
                "metadata": {"avg_price": 400, "distance_km": 5, "tags": ["法餐", "浪漫", "私密", "fine_dining", "仪式感"]},
            },
            {
                "poi_id": "poi_rest_302",
                "name": "鮨然日本料理",
                "category": "日料",
                "score": 0.87,
                "reason": "Omakase，安静板前，氛围感好",
                "metadata": {"avg_price": 350, "distance_km": 6, "tags": ["日料", "安静", "精致", "仪式感", "吧台"]},
            },
            {
                "poi_id": "poi_rest_303",
                "name": "花厨（三里屯）",
                "category": "创意菜",
                "score": 0.84,
                "reason": "鲜花主题餐厅，出片率高，女生最爱",
                "metadata": {"avg_price": 220, "distance_km": 3, "tags": ["创意菜", "拍照", "浪漫", "出片"]},
            },
            {
                "poi_id": "poi_rest_304",
                "name": "大董烤鸭（工体店）",
                "category": "中餐",
                "score": 0.82,
                "reason": "环境雅致，适合需要体面约会的场合",
                "metadata": {"avg_price": 300, "distance_km": 4, "tags": ["中餐", "烤鸭", "雅致", "体面"]},
            },
        ],
        "加餐": [
            {
                "poi_id": "poi_flower_010",
                "name": "野兽派 小花束（送餐到桌）",
                "category": "花",
                "score": 0.82,
                "reason": "精致花束，约会仪式感满分",
                "metadata": {"avg_price": 120, "distance_km": 0, "tags": ["花", "礼物", "浪漫", "仪式感"]},
            },
            {
                "poi_id": "poi_cake_008",
                "name": "黑天鹅蛋糕（国贸店）",
                "category": "蛋糕",
                "score": 0.80,
                "reason": "高端甜点，约会加分项",
                "metadata": {"avg_price": 180, "distance_km": 2, "tags": ["蛋糕", "甜点", "精致", "高端"]},
            },
            {
                "poi_id": "poi_coffee_002",
                "name": "% Arabica（三里屯）",
                "category": "咖啡",
                "score": 0.76,
                "reason": "网红咖啡，拍照打卡两不误",
                "metadata": {"avg_price": 38, "distance_km": 1, "tags": ["咖啡", "网红", "拍照"]},
            },
        ],
    },

    # ═══════════════════════════════════════════════════════════════
    # solo — 个人放松
    # ═══════════════════════════════════════════════════════════════
    "solo": {
        "玩": [
            {
                "poi_id": "poi_solo_001",
                "name": "PageOne 书店（前门店）",
                "category": "书店",
                "score": 0.85,
                "reason": "安静看书喝咖啡，独处好去处",
                "metadata": {"avg_price": 0, "distance_km": 5, "tags": ["安静", "阅读", "室内", "独处"]},
            },
            {
                "poi_id": "poi_solo_002",
                "name": "地坛公园",
                "category": "公园",
                "score": 0.78,
                "reason": "散步发呆，一个人也很自在",
                "metadata": {"avg_price": 2, "distance_km": 3, "tags": ["公园", "户外", "免费", "散步"]},
            },
            {
                "poi_id": "poi_solo_003",
                "name": "单向空间书店",
                "category": "书店",
                "score": 0.82,
                "reason": "文艺氛围，有讲座和签售",
                "metadata": {"avg_price": 0, "distance_km": 4, "tags": ["安静", "阅读", "室内", "文化"]},
            },
        ],
        "吃": [
            {
                "poi_id": "poi_rest_401",
                "name": "一风堂拉面",
                "category": "日式简餐",
                "score": 0.80,
                "reason": "一人食友好，吧台位不尴尬",
                "metadata": {"avg_price": 65, "distance_km": 2, "tags": ["日式", "快速", "一人食", "性价比"]},
            },
            {
                "poi_id": "poi_rest_402",
                "name": "沙县小吃",
                "category": "快餐",
                "score": 0.60,
                "reason": "便宜管饱，不纠结",
                "metadata": {"avg_price": 20, "distance_km": 1, "tags": ["快餐", "便宜", "快速"]},
            },
            {
                "poi_id": "poi_rest_403",
                "name": "Wagas 轻食",
                "category": "轻食",
                "score": 0.75,
                "reason": "一个人吃饭不尴尬，健康轻食",
                "metadata": {"avg_price": 78, "distance_km": 3, "tags": ["轻食", "健康", "一人食"]},
            },
        ],
        "加餐": [
            {
                "poi_id": "poi_coffee_003",
                "name": "瑞幸咖啡（路边自取）",
                "category": "咖啡",
                "score": 0.68,
                "reason": "9.9 一杯，拿了就走",
                "metadata": {"avg_price": 10, "distance_km": 0, "tags": ["咖啡", "便宜", "快速"]},
            },
            {
                "poi_id": "poi_tea_003",
                "name": "蜜雪冰城",
                "category": "奶茶",
                "score": 0.55,
                "reason": "柠檬水 4 块，便宜解渴",
                "metadata": {"avg_price": 6, "distance_km": 0, "tags": ["奶茶", "便宜", "快速"]},
            },
        ],
    },
}


def search(
    scene: str,
    stage: str,
    limit: int = 10,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """按 scene + stage 查 POI；可选 category 过滤。

    scene 缺省回退到 family；stage 不存在返回空。
    category 非空时优先返回匹配的 POI，再补其他结果到 limit。
    """
    bucket = CATALOG.get(scene) or CATALOG.get("family") or {}
    items = bucket.get(stage, [])

    if category and items:
        # 优先匹配 category 或 tags 中含有关键词的 POI
        cat_lower = category.lower()
        matched: list[dict[str, Any]] = []
        rest: list[dict[str, Any]] = []
        for item in items:
            tags = item.get("metadata", {}).get("tags", [])
            item_cat = item.get("category", "").lower()
            if cat_lower in item_cat or any(cat_lower in str(t).lower() for t in tags):
                matched.append(item)
            else:
                rest.append(item)
        items = matched + rest

    return list(items[:limit])
