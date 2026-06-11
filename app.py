import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ssl_cert = os.environ.get("SSL_CERT_FILE", "")
if ssl_cert and not os.path.exists(ssl_cert):
    fixed = ssl_cert.replace("miniconda3/ssl/", "miniconda3/Library/ssl/").replace("miniconda3\\ssl\\", "miniconda3\\Library\\ssl\\")
    if os.path.exists(fixed):
        os.environ["SSL_CERT_FILE"] = fixed
    else:
        os.environ.pop("SSL_CERT_FILE", None)

st.set_page_config(
    page_title="Playable Ad Generator",
    page_icon="🎮",
    layout="wide",
)

st.title("🎮 智能试玩广告生成器")
st.caption("提供玩法描述 + 产品链接 + 参考试玩 → AI 自动生成三渠道试玩HTML")

api_key = os.getenv("ANTHROPIC_API_KEY", "")

with st.sidebar:
    st.header("⚙️ 配置")
    api_key_input = st.text_input(
        "Anthropic API Key",
        value=api_key,
        type="password",
        help="如未设置环境变量，请在此输入"
    )
    if api_key_input:
        api_key = api_key_input

    base_url = st.text_input(
        "API Base URL",
        value=os.getenv("ANTHROPIC_BASE_URL", ""),
        help="第三方代理地址，如不使用留空即可"
    )

    model_name = st.text_input(
        "模型名称",
        value=os.getenv("ANTHROPIC_MODEL", "ppio/pa/claude-sonnet-4-6"),
        help="你的API提供商支持的模型ID，如 claude-sonnet-4-6, claude-3-5-sonnet-20241022"
    )

    st.divider()
    st.header("📊 输出设置")
    output_dir = st.text_input("输出目录", value=str(Path(__file__).parent / "output"))

    st.divider()
    st.markdown("**渠道文件大小限制**")
    st.markdown("- Unity: < 5MB")
    st.markdown("- AppLovin: < 5MB")
    st.markdown("- Google UAC: < 5MB")

col1, col2 = st.columns([3, 2])

GAME_CATEGORIES = {
    "🎨 涂色 (Color by Number)": "涂色/Color-by-Number游戏。玩家从调色板选择颜色，点击对应编号的区域进行填色。",
    "🧩 拼图 (Puzzle/Jigsaw)": "拼图游戏。4x4网格，拖拽交换碎片位置还原完整图片。",
    "🃏 拼图纸牌 (JigSolitaire)": "拼图纸牌试玩。提供多种模板：核心玩法、动图+核心、纯动图拼接、不规则碎片，上传对应素材秒级生成。",
    "💎 三消 (Match-3)": "三消/货架消除游戏。滑动或点击匹配3个以上相同物品进行消除，上方物品下落补位。",
    "🀄 麻将 (Mahjong Match)": "麻将配对消除。在牌面中找到相同的两张牌点击消除，逐步清空牌面。",
    "🔍 找不同 (Spot Difference)": "找不同游戏。两张几乎相同的图片并排，找出其中的差异处并点击标记。",
    "➡️ 箭头 (Arrow Puzzle)": "箭头解谜游戏。网格中有多个指向不同方向的箭头，点击旋转箭头方向，使所有箭头形成通往出口的连通路径。",
    "🧪 水排序 (Water Sort)": "水排序游戏。多个瓶子中装有混合颜色的液体层，点击瓶子将顶层液体倒入另一个瓶子，最终让每个瓶子只有单一颜色。",
    "✏️ 自定义": "",
}

with col1:
    st.header("📝 输入信息")

    game_category = st.selectbox(
        "🎮 游戏品类",
        options=list(GAME_CATEGORIES.keys()),
        index=0,
        help="选择品类后会自动填充玩法描述模板，你可以在此基础上修改"
    )

    category_hint = GAME_CATEGORIES[game_category]

    gameplay_desc = st.text_area(
        "玩法描述",
        height=200,
        value=category_hint if category_hint else "",
        placeholder="详细描述游戏的核心玩法机制...\n\n"
                    "选择上方品类可自动填充模板描述，你可以在此基础上补充细节，如：\n"
                    "- 视觉风格（卡通/写实/像素）\n"
                    "- 具体的网格大小、物品种类\n"
                    "- 特殊机制（combo、时间限制等）",
    )

    store_url = st.text_input(
        "产品商店链接",
        placeholder="https://play.google.com/store/apps/details?id=com.example.game",
    )

    st.subheader("📎 参考试玩文件（可选）")
    reference_files = st.file_uploader(
        "上传参考试玩HTML文件（支持多选），AI会分析其结构和玩法逻辑",
        type=["html", "htm"],
        accept_multiple_files=True,
    )

    st.subheader("🖼️ 素材文件（可选）")
    is_coloring_hint = '涂色' in game_category or 'Color' in game_category
    is_mahjong_hint = '麻将' in game_category or 'Mahjong' in game_category
    is_finddiff_hint = '找不同' in game_category or 'Difference' in game_category
    is_arrow_hint = '箭头' in game_category or 'Arrow' in game_category
    is_jigsol_hint = '拼图纸牌' in game_category or 'JigSolitaire' in game_category
    is_puzzle_hint = (not is_jigsol_hint) and ('拼图' in game_category or 'Jigsaw' in game_category
                      or ('Puzzle' in game_category and not is_arrow_hint))
    is_match3_hint = ('三消' in game_category or 'Match' in game_category) and not is_mahjong_hint
    is_hidden_hint = '找物' in game_category or 'Hidden' in game_category
    JIGSOL_TEMPLATES = {
        "核心玩法（复古）": "core",
        "动图前贴 + 核心玩法": "video_core",
        "纯动图状态下拼接": "video_only",
        "不规则碎片": "irregular",
    }
    jigsol_mode = "core"
    if is_jigsol_hint:
        _jig_choice = st.radio(
            "🃏 拼图纸牌模板",
            options=list(JIGSOL_TEMPLATES.keys()),
            index=0,
            help="选择不同试玩模板，每种对应不同素材：核心/不规则=1张图；动图+核心=1段视频；纯动图=1段视频。",
        )
        jigsol_mode = JIGSOL_TEMPLATES[_jig_choice]
        _need = {
            "core": "上传 **1 张完整图片**（建议竖图 ≈ 2:3，如 1365×2048）作为拼图原图",
            "irregular": "上传 **1 张完整图片**（建议竖图 ≈ 2:3，如 500×750）→ 自动切成 24 块凸凹互锁碎片",
            "video_core": "上传 **1 段视频（MP4）** 作为前贴片动图；拼图原图自动取视频末帧",
            "video_only": "上传 **1 段视频（MP4）**；视频边播放边作为拼图内容进行拼接",
        }[jigsol_mode]
        st.info(
            "**拼图纸牌（JigSolitaire）— " + _jig_choice + "：**\n"
            "- " + _need + "\n"
            "- 玩法：拖拽碎片交换/吸附归位，全部还原即胜利\n"
            "- 无需 API Key，本地秒级生成。"
            + ("\n\n⚠️ 视频模板成品较大，请用短视频（建议 < 3MB）以满足渠道 5MB 限制。" if jigsol_mode in ("video_core","video_only") else "")
        )
    match3_mode = "固定货架（拖拽叠放消除）"
    if is_match3_hint:
        match3_mode = st.radio(
            "🎮 三消玩法",
            options=["固定货架（拖拽叠放消除）", "移动货架（点击收集消除）"],
            index=0,
            help="固定货架：拖拽物品叠放3个相同消除。移动货架：货架横向滚动，点击3个相同物品收集进上方柜子。",
        )
        st.info(
            "**三消品类素材要求：**\n"
            "- 上传多张物品图片（每张为一种物品类型）\n"
            "- 建议正方形 PNG/WebP，至少6种，最多9种\n"
            "- 不上传图片则使用内置 emoji 物品\n\n"
            "无需 API Key，本地秒级生成。"
        )
    elif is_mahjong_hint:
        st.info(
            "**麻将品类素材要求：**\n"
            "- 玩法：经典麻将连连消，点击两张相同的“自由牌”配对消除，清空牌面即胜利\n"
            "- 可上传多张牌面图片（每张为一种牌型，建议正方形 PNG/WebP）\n"
            "- 不上传图片则使用内置麻将牌面\n\n"
            "无需 API Key，本地秒级生成。"
        )
    elif is_coloring_hint:
        st.info(
            "**涂色品类素材要求：**\n"
            "- `_region.svg` — 区域着色文件（必须，Illustrator导出，含 .stX 颜色样式 + path路径）\n"
            "- `_color.png/jpg/webp` — 完成效果颜色参考图（可选）\n"
            "- `_outline.pdf` — 线稿文件（可选）\n\n"
            "上传 SVG 区域文件后无需 API Key，本地秒级生成。"
        )
    elif is_puzzle_hint:
        st.info(
            "**拼图品类素材要求：**\n"
            "- 上传一张完整图片（png/jpg/webp）作为拼图原图\n"
            "- 系统自动切割为 24 块经典凸凹互锁碎片\n"
            "- 无需 API Key，本地秒级生成。"
        )
    elif is_finddiff_hint:
        st.info(
            "**找不同品类素材要求（两种方式任选）：**\n"
            "1. **关卡包（推荐）**：上传一套 `*_base.jpg`（底图）+ `*_atlas.png`（差异图集）+ `*_level.json`（关卡数据），"
            "系统自动合成差异图并换算坐标。\n"
            "2. **手动方式**：上传两张图片（原图 A + 差异图 B）+ 一个不同点坐标 `.json`，如\n"
            "  `[{\"x\":0.32,\"y\":0.58,\"r\":0.06}, ...]`（x/y 为相对图宽高的 0~1 比例，r 为命中半径）\n"
            "- 找全所有不同点即胜利。无需 API Key，本地秒级生成。"
        )
    elif is_arrow_hint:
        st.info(
            "**箭头解谜品类（Arrows Escape）：**\n"
            "- 玩法：点击箭头，箭头沿朝向直线飞出棋盘被消除；前进路径被其他箭头挡住则点击无效、扣 1 命；清空全部箭头即胜利\n"
            "- **上传一个关卡 `level.json`**（Unity 导出格式：含 `FormationData` + `ArrowLineDatas[].Points`），系统自动解析坐标生成\n"
            "- 不上传则随机生成一个可解关卡\n"
            "- 无需 API Key，本地秒级生成。"
        )
    elif is_hidden_hint:
        st.info(
            "**找物品类（Hidden Object）：**\n"
            "- 玩法：在复杂场景中找到指定的隐藏物品并点击，找全所有物品即胜利\n"
            "- **上传一张场景图片**（PNG/JPG/WebP）作为背景\n"
            "- **上传一个物品坐标 `.json`**，格式如：\n"
            "  `[{\"x\":0.3,\"y\":0.5,\"r\":0.08,\"name\":\"Item1\",\"thumb\":\"...\"}]`\n"
            "  x/y 为相对图宽高的 0~1 比例，r 为命中半径，name 为物品名称，thumb 为物品缩略图（可选）\n"
            "- 可选：上传物品缩略图图片（系统自动分配给物品）\n"
            "- 无需 API Key，本地秒级生成。"
        )
    water_mode = "明水排序"
    water_difficulty = "中等（9瓶）"
    if is_water_hint:
        water_mode = st.radio(
            "🧪 水排序模式",
            options=["明水排序", "暗水排序"],
            index=0,
            help="明水排序：所有颜色可见。暗水排序：只能看到最上层颜色，倒掉后才能看到下一层。",
        )
        water_difficulty = st.radio(
            "📊 水排序难度",
            options=["简单（5瓶）", "中等（9瓶）", "困难（15瓶）"],
            index=1,
            help="简单：5瓶3色。中等：9瓶5色。困难：15瓶7色。",
        )
        st.info(
            "**水排序品类：**\n"
            "- 玩法：点击瓶子将顶层液体倒入另一个瓶子，最终让每个瓶子只有单一颜色\n"
            "- 无需上传素材，无需 API Key，本地秒级生成\n"
            "- 每次生成随机布局，保证可解"
        )
    if is_arrow_hint:
        _uploader_label = "上传关卡 level.json（Unity 导出，可不传则随机生成）"
        _uploader_types = ["png", "jpg", "jpeg", "webp", "svg", "pdf", "json"]
    elif is_hidden_hint:
        _uploader_label = "上传场景图片 + 物品坐标JSON（可选物品缩略图）"
        _uploader_types = ["png", "jpg", "jpeg", "webp", "json"]
    elif is_jigsol_hint and jigsol_mode in ("video_core", "video_only"):
        _uploader_label = "上传 1 段视频（MP4）"
        _uploader_types = ["mp4", "webm", "mov"]
    elif is_jigsol_hint:
        _uploader_label = "上传 1 张完整图片（拼图原图）"
        _uploader_types = ["png", "jpg", "jpeg", "webp"]
    else:
        _uploader_label = "上传素材文件（支持多选，第一张作为主图，第二张作为背景图）"
        _uploader_types = ["png", "jpg", "jpeg", "webp", "svg", "pdf", "json"]
    asset_files = st.file_uploader(
        _uploader_label,
        type=_uploader_types,
        accept_multiple_files=True,
    )

with col2:
    st.header("🎯 生成")

    if not api_key:
        st.warning("请先配置 Anthropic API Key")

    is_coloring_category = '涂色' in game_category or 'Color' in game_category
    is_mahjong_category = '麻将' in game_category or 'Mahjong' in game_category
    is_finddiff_category = '找不同' in game_category or 'Difference' in game_category
    is_arrow_category = '箭头' in game_category or 'Arrow' in game_category
    is_jigsol_category = '拼图纸牌' in game_category or 'JigSolitaire' in game_category
    is_match3_category = ('三消' in game_category or 'Match' in game_category) and not is_mahjong_category
    is_water_category = '水排序' in game_category or 'Water' in game_category
    is_blind_category = '暗水排序' in game_category or 'Blind' in game_category
    is_hidden_category = '找物' in game_category or 'Hidden' in game_category
    no_api_needed = is_coloring_category or is_match3_category or is_mahjong_category or is_finddiff_category or is_arrow_category or is_jigsol_category or is_water_category or is_blind_category or is_hidden_category
    generate_btn = st.button(
        "🚀 生成试玩广告",
        type="primary",
        use_container_width=True,
        disabled=not ((api_key or no_api_needed) and store_url),
    )

    if generate_btn:
        from core.post_processor import process_all_channels
        from core.svg_parser import detect_region_svg

        full_desc = f"[游戏品类: {game_category}]\n\n{gameplay_desc}"

        reference_html = None
        if reference_files:
            parts = []
            for rf in reference_files:
                parts.append(f"<!-- === {rf.name} === -->\n{rf.read().decode('utf-8', errors='ignore')}")
            reference_html = "\n\n".join(parts)

        assets = {}
        svg_region_content = None
        if asset_files:
            for af in asset_files:
                file_data = af.read()
                if detect_region_svg(file_data, af.name):
                    svg_region_content = file_data.decode('utf-8', errors='ignore')
                elif not assets.get('main_image'):
                    assets['main_image'] = file_data
                    assets['main_image_name'] = af.name
                elif not assets.get('bg_image'):
                    assets['bg_image'] = file_data
                    assets['bg_image_name'] = af.name

        is_mahjong = '麻将' in game_category or 'Mahjong' in game_category
        is_match3 = ('三消' in game_category or 'Match' in game_category) and not is_mahjong
        is_coloring = '涂色' in game_category or 'Color' in game_category
        is_arrow = '箭头' in game_category or 'Arrow' in game_category
        is_jigsol = '拼图纸牌' in game_category or 'JigSolitaire' in game_category
        is_puzzle = (not is_jigsol) and ('拼图' in game_category or 'Jigsaw' in game_category
                     or ('Puzzle' in game_category and not is_arrow))
        is_finddiff = '找不同' in game_category or 'Difference' in game_category
        is_hidden = '找物' in game_category or 'Hidden' in game_category
        is_water = '水排序' in game_category or 'Water' in game_category
        is_blind = '暗水排序' in game_category or 'Blind' in game_category
        use_match3_template = is_match3
        use_mahjong_template = is_mahjong
        use_coloring_template = is_coloring and svg_region_content is not None
        use_puzzle_template = is_puzzle and assets.get('main_image')
        use_finddiff_template = is_finddiff
        use_arrow_template = is_arrow
        use_jigsol_template = is_jigsol
        use_water_sort_template = is_water and not is_blind
        use_blind_sort_template = is_blind
        use_hidden_template = is_hidden

        if use_match3_template:
            from core.template_generator import generate_match3_shelf, generate_match3_moving, generate_match3_drag
            from core.media import make_data_uri_from_bytes

            is_moving = '移动货架' in match3_mode
            is_drag = '柜格三消' in match3_mode

            with st.status("正在生成三消试玩广告...", expanded=True) as status:
                if is_drag:
                    _mode_label = "柜格三消"
                elif is_moving:
                    _mode_label = "移动货架"
                else:
                    _mode_label = "固定货架"
                st.write("🎮 生成货架消除模板（" + _mode_label + "）...")
                try:
                    tile_data = None
                    if asset_files:
                        tile_data = []
                        for af in asset_files:
                            af.seek(0)
                            file_data = af.read()
                            mime = 'image/png'
                            if af.name.lower().endswith('.webp'):
                                mime = 'image/webp'
                            elif af.name.lower().endswith(('.jpg', '.jpeg')):
                                mime = 'image/jpeg'
                            data_uri = make_data_uri_from_bytes(file_data, mime)
                            tile_data.append(data_uri)
                        st.write(f"📎 已加载 {len(tile_data)} 种物品图片")

                    if is_drag:
                        html_code = generate_match3_drag(
                            store_url=store_url,
                            tile_data=tile_data,
                        )
                    elif is_moving:
                        html_code = generate_match3_moving(
                            store_url=store_url,
                            tile_data=tile_data,
                        )
                    else:
                        html_code = generate_match3_shelf(
                            store_url=store_url,
                            tile_data=tile_data,
                        )
                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        output_dir=output_dir,
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None

        elif use_mahjong_template:
            from core.template_generator import generate_mahjong_match
            from core.media import make_data_uri_from_bytes

            with st.status("正在生成麻将试玩广告...", expanded=True) as status:
                st.write("🀄 生成麻将连连消模板...")
                try:
                    tile_data = None
                    if asset_files:
                        tile_data = []
                        for af in asset_files:
                            af.seek(0)
                            file_data = af.read()
                            mime = 'image/png'
                            if af.name.lower().endswith('.webp'):
                                mime = 'image/webp'
                            elif af.name.lower().endswith(('.jpg', '.jpeg')):
                                mime = 'image/jpeg'
                            data_uri = make_data_uri_from_bytes(file_data, mime)
                            tile_data.append(data_uri)
                        st.write(f"📎 已加载 {len(tile_data)} 种牌面图片")

                    html_code = generate_mahjong_match(
                        store_url=store_url,
                        tile_data=tile_data,
                    )
                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        output_dir=output_dir,
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None

        elif use_finddiff_template:
            import json as _json
            from core.template_generator import generate_find_differences, compose_finddiff_from_levelpack
            from core.media import make_data_uri_from_bytes

            with st.status("正在生成找不同试玩广告...", expanded=True) as status:
                st.write("🔍 生成找不同模板...")
                try:
                    images = []          # (bytes, mime) for simple A/B mode
                    diffs = None         # normalized [{x,y,r}]
                    level = None         # production level.json dict
                    base_bytes = None    # level-pack base image
                    atlas_bytes = None   # level-pack atlas image
                    if asset_files:
                        for af in asset_files:
                            af.seek(0)
                            data = af.read()
                            name = af.name.lower()
                            if name.endswith('.json'):
                                try:
                                    parsed = _json.loads(data.decode('utf-8', errors='ignore'))
                                except Exception as je:
                                    st.warning(f"JSON 解析失败：{je}")
                                    parsed = None
                                if isinstance(parsed, dict) and 'items' in parsed:
                                    level = parsed          # production level pack
                                elif isinstance(parsed, list):
                                    diffs = parsed          # simple normalized list
                            elif name.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                                mime = 'image/png'
                                if name.endswith('.webp'):
                                    mime = 'image/webp'
                                elif name.endswith(('.jpg', '.jpeg')):
                                    mime = 'image/jpeg'
                                if 'atlas' in name:
                                    atlas_bytes = data
                                elif 'base' in name:
                                    base_bytes = data
                                else:
                                    images.append((data, mime))

                    if level is not None:
                        # production level pack: base + atlas + level.json
                        if base_bytes is None and images:
                            base_bytes = images[0][0]
                        if atlas_bytes is None and len(images) > 1:
                            atlas_bytes = images[1][0]
                        if base_bytes is None or atlas_bytes is None:
                            raise ValueError("关卡包模式需要 base 底图、atlas 图集 和 level.json 三个文件（文件名建议含 base / atlas）。")
                        st.write("🧩 检测到关卡包格式，正在合成差异图...")
                        a_bytes, b_bytes, diffs = compose_finddiff_from_levelpack(base_bytes, atlas_bytes, level)
                        img_a = make_data_uri_from_bytes(a_bytes, 'image/jpeg')
                        img_b = make_data_uri_from_bytes(b_bytes, 'image/jpeg')
                        st.write(f"✅ 已合成原图/差异图 + {len(diffs)} 个不同点")
                    else:
                        if len(images) < 2:
                            raise ValueError("找不同需要上传两张图片（原图 A + 差异图 B），或上传一套关卡包（base + atlas + level.json）。")
                        if not diffs:
                            raise ValueError("找不同需要上传一个不同点坐标 .json，如 [{\"x\":0.3,\"y\":0.5,\"r\":0.06}]，或上传 level.json 关卡包。")
                        img_a = make_data_uri_from_bytes(images[0][0], images[0][1])
                        img_b = make_data_uri_from_bytes(images[1][0], images[1][1])
                        st.write(f"📎 已加载 2 张图片 + {len(diffs)} 个不同点坐标")

                    html_code = generate_find_differences(
                        store_url=store_url,
                        image_a=img_a,
                        image_b=img_b,
                        diffs=diffs,
                    )
                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        output_dir=output_dir,
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None

        elif use_arrow_template:
            import json as _json
            from core.template_generator import generate_arrow_puzzle, parse_unity_arrow_level

            with st.status("正在生成箭头解谜试玩广告...", expanded=True) as status:
                try:
                    level_arrows = None
                    grid_n = None
                    if asset_files:
                        for af in asset_files:
                            if not af.name.lower().endswith('.json'):
                                continue
                            af.seek(0)
                            raw = af.read().decode('utf-8', errors='ignore')
                            try:
                                level = _json.loads(raw)
                            except Exception as je:
                                raise ValueError(f"level.json 解析失败：{je}")
                            level_arrows, grid_n = parse_unity_arrow_level(level)
                            st.write(f"📐 已解析关卡 `{af.name}`：{len(level_arrows)} 个箭头，棋盘 {grid_n}×{grid_n}")
                            break

                    if level_arrows:
                        st.write("🧭 按上传关卡生成箭头模板...")
                        html_code = generate_arrow_puzzle(
                            store_url=store_url,
                            arrows=level_arrows,
                            grid_size=[grid_n, grid_n],
                        )
                    else:
                        st.write("🧭 未检测到 level.json，随机生成可解关卡...")
                        html_code = generate_arrow_puzzle(store_url=store_url)

                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        output_dir=output_dir,
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None

        elif use_jigsol_template:
            from core.template_generator import (
                generate_jig_core, generate_jig_irregular,
                generate_jig_video_core, generate_jig_video_only,
            )
            from core.media import make_data_uri_from_bytes

            with st.status("正在生成拼图纸牌试玩广告...", expanded=True) as status:
                try:
                    needs_video = jigsol_mode in ("video_core", "video_only")
                    up = None
                    if asset_files:
                        up = asset_files[0]
                        up.seek(0)
                    if up is None:
                        raise ValueError("请上传素材：图片模板需 1 张图片；视频模板需 1 段 MP4。")

                    data = up.read()
                    name = up.name.lower()
                    if needs_video:
                        mime = 'video/mp4'
                        if name.endswith('.webm'):
                            mime = 'video/webm'
                        elif name.endswith('.mov'):
                            mime = 'video/quicktime'
                        uri = make_data_uri_from_bytes(data, mime)
                        st.write(f"🎬 已加载视频 `{up.name}`（{len(data)/1024/1024:.2f}MB）")
                        if jigsol_mode == "video_core":
                            html_code = generate_jig_video_core(store_url=store_url, video_data_uri=uri)
                        else:
                            html_code = generate_jig_video_only(store_url=store_url, video_data_uri=uri)
                    else:
                        # compress the puzzle image (resize + to JPEG) so the playable
                        # stays small and renders reliably; keep a higher resolution
                        # than the default since it's the main visual.
                        from core.media import compress_image
                        img_bytes, out_mime = compress_image(data, max_kb=900, max_width=1200, max_height=1600)
                        uri = make_data_uri_from_bytes(img_bytes, out_mime)
                        st.write(f"🖼️ 已加载图片 `{up.name}`（压缩后 {len(img_bytes)/1024:.0f}KB）")
                        if jigsol_mode == "irregular":
                            html_code = generate_jig_irregular(store_url=store_url, image_data_uri=uri)
                        else:
                            html_code = generate_jig_core(store_url=store_url, image_data_uri=uri)

                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        output_dir=output_dir,
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None

        elif use_coloring_template:
            from core.template_generator import generate_color_by_number

            with st.status("正在生成涂色试玩广告...", expanded=True) as status:
                st.write("📐 解析 SVG 区域数据...")
                try:
                    html_code = generate_color_by_number(
                        svg_content=svg_region_content,
                        store_url=store_url,
                        num_blocks=12,
                    )
                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        assets=assets if assets else None,
                        output_dir=output_dir,
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None
        elif use_puzzle_template:
            from core.template_generator import generate_jigsaw_puzzle

            with st.status("正在生成拼图试玩广告...", expanded=True) as status:
                st.write("🧩 生成拼图模板...")
                try:
                    html_code = generate_jigsaw_puzzle(
                        store_url=store_url,
                    )
                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配（嵌入图片）...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        assets=assets,
                        output_dir=output_dir,
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None
        elif use_water_sort_template:
            from core.template_generator import generate_water_sort

            with st.status("正在生成水排序试玩广告...", expanded=True) as status:
                # 根据难度设置参数
                if '简单' in water_difficulty:
                    colors, empty, cap = 3, 2, 3
                    total = 5
                elif '困难' in water_difficulty:
                    colors, empty, cap = 7, 2, 4
                    total = 15
                else:  # 中等
                    colors, empty, cap = 5, 2, 4
                    total = 9

                st.write(f"🧪 生成水排序模板（{total}瓶/{colors}色/{empty}空瓶）...")
                try:
                    html_code = generate_water_sort(
                        store_url=store_url,
                        colors=colors,
                        empty=empty,
                        cap=cap,
                    )
                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        output_dir=output_dir,
                        product_name=f'watersort-{water_difficulty[:2]}',
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None
        elif use_blind_sort_template:
            from core.template_generator import generate_water_sort_blind

            with st.status("正在生成暗水排序试玩广告...", expanded=True) as status:
                # 根据难度设置参数
                if '简单' in water_difficulty:
                    colors, empty, cap = 3, 2, 3
                    total = 5
                elif '困难' in water_difficulty:
                    colors, empty, cap = 7, 2, 4
                    total = 15
                else:  # 中等
                    colors, empty, cap = 5, 2, 4
                    total = 9

                st.write(f"🔮 生成暗水排序模板（{total}瓶/{colors}色）...")
                try:
                    html_code = generate_water_sort_blind(
                        store_url=store_url,
                        colors=colors,
                        empty=empty,
                        cap=cap,
                    )
                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        output_dir=output_dir,
                        product_name=f'blindsort-{water_difficulty[:2]}',
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None
        elif use_hidden_template:
            from core.template_generator import generate_hidden_object
            from core.media import make_data_uri_from_bytes

            with st.status("正在生成找物试玩广告...", expanded=True) as status:
                st.write("🔍 生成找物模板...")
                try:
                    scene_uri = None
                    items = []
                    if asset_files:
                        for af in asset_files:
                            af.seek(0)
                            file_data = af.read()
                            name = af.name.lower()
                            if name.endswith('.json'):
                                import json as _json
                                try:
                                    item_data = _json.loads(file_data.decode('utf-8', errors='ignore'))
                                    if isinstance(item_data, list):
                                        items = item_data
                                except Exception as je:
                                    st.warning(f"JSON 解析失败：{je}")
                            elif name.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                                mime = 'image/png'
                                if name.endswith('.webp'):
                                    mime = 'image/webp'
                                elif name.endswith(('.jpg', '.jpeg')):
                                    mime = 'image/jpeg'
                                if not scene_uri:
                                    scene_uri = make_data_uri_from_bytes(file_data, mime)
                                else:
                                    thumb_uri = make_data_uri_from_bytes(file_data, mime)
                                    for item in items:
                                        if not item.get('thumb'):
                                            item['thumb'] = thumb_uri
                                            break

                    if not scene_uri:
                        raise ValueError("请上传一张场景图片作为背景。")

                    if not items:
                        raise ValueError("请上传一个物品坐标 JSON 文件，格式如：[{\"x\":0.3,\"y\":0.5,\"r\":0.08,\"name\":\"Item1\"}]")

                    st.write(f"📎 已加载场景图 + {len(items)} 个物品")

                    html_code = generate_hidden_object(
                        store_url=store_url,
                        scene_data_uri=scene_uri,
                        items=items,
                    )
                    st.write(f"✅ 模板生成完成（{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        output_dir=output_dir,
                    )
                    status.update(label="✅ 生成完成！", state="complete")
                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None
        else:
            from core.ai_generator import PlayableAdGenerator

            with st.status("正在生成试玩广告...", expanded=True) as status:
                st.write("🤖 调用 AI 生成游戏代码...")

                generator = PlayableAdGenerator(
                    api_key=api_key,
                    model=model_name,
                    base_url=base_url if base_url else None,
                )

                ESTIMATED_TOKENS = 12000
                progress_bar = st.progress(0, text="准备中...")
                collected_tokens = []

                def on_token(token):
                    collected_tokens.append(token)
                    count = len(collected_tokens)
                    pct = min(count / ESTIMATED_TOKENS, 0.95)
                    if count % 20 == 0:
                        progress_bar.progress(pct, text=f"AI 生成中... {int(pct*100)}%（{count} tokens）")

                try:
                    html_code = generator.generate(
                        gameplay_desc=full_desc,
                        store_url=store_url,
                        reference_html=reference_html,
                        has_main_image=bool(assets.get('main_image')),
                        on_token=on_token,
                    )

                    progress_bar.progress(1.0, text=f"✅ AI 生成完成（{len(collected_tokens)} tokens，{len(html_code)} 字符）")
                    st.write("📦 正在进行三渠道适配...")

                    results = process_all_channels(
                        html=html_code,
                        store_url=store_url,
                        assets=assets if assets else None,
                        output_dir=output_dir,
                    )

                    status.update(label="✅ 生成完成！", state="complete")

                except Exception as e:
                    status.update(label="❌ 生成失败", state="error")
                    st.error(f"错误: {str(e)}")
                    results = None

        if results:
            st.divider()
            st.subheader("📁 输出结果")

            first_info = next(iter(results.values()))
            if not first_info.get('js_valid', True):
                st.error(f"⚠️ JavaScript 语法错误（试玩可能无法运行）:\n```\n{first_info['js_error'][:300]}\n```")

            for channel_key, info in results.items():
                size_str = f"{info['size_mb']:.2f}MB"
                limit_str = f"{info['max_mb']}MB"
                icon = "✅" if info['within_limit'] and info.get('js_valid', True) else "⚠️"
                st.markdown(f"**{icon} {channel_key.upper()}** — {size_str} / {limit_str}")
                st.code(info['path'], language=None)

                with open(info['path'], 'rb') as f:
                    st.download_button(
                        f"⬇️ 下载 {channel_key.upper()}",
                        data=f.read(),
                        file_name=Path(info['path']).name,
                        mime="text/html",
                    )

            st.divider()
            st.subheader("👁️ 预览")
            preview_channel = st.selectbox("选择预览渠道", list(results.keys()))
            if preview_channel:
                st.components.v1.html(results[preview_channel]['html'], height=700, scrolling=False)

st.divider()
st.caption("Powered by Claude AI | 三渠道: Unity / AppLovin / Google UAC")
