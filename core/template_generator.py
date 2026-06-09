import json
import random
from pathlib import Path

from .svg_parser import parse_svg, detect_region_svg

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_match3_shelf(store_url: str, rows: int = 8, cols: int = 3, goal: int = 8, tile_data: list = None) -> str:
    """Generate a Match-3 Shelf playable ad HTML.

    Args:
        store_url: App store URL for CTA
        rows: Number of shelf rows
        cols: Number of shelf columns
        goal: Number of clears to win
        tile_data: Optional list of base64 data URIs for tile images

    Returns:
        Complete HTML string ready for post-processing
    """
    template_path = TEMPLATES_DIR / "match3_shelf.html"
    template = template_path.read_text(encoding='utf-8')
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    template = template.replace('{{COLS}}', str(cols))
    template = template.replace('{{ROWS}}', str(rows))
    template = template.replace('{{GOAL}}', str(goal))

    if tile_data:
        tile_json = json.dumps(tile_data, separators=(',', ':'))
        template = template.replace('/*{{TILE_DATA}}*/null', tile_json)

    return template


def generate_match3_moving(store_url: str, goal: int = 8, tile_data: list = None) -> str:
    """Generate a moving-shelf Match-3 (tap-to-collect) playable ad HTML.

    Mechanic: horizontally scrolling shelf rows (rAF dual-track loop); tap 3
    matching items to fill a cabinet; clear `goal` cabinets to win. Emoji
    fallback when no tile_data; synth SFX, no embedded BGM.

    Args:
        store_url: App store URL for CTA
        goal: Number of cabinet clears to win
        tile_data: Optional list of base64 data URIs for tile images (by type index)

    Returns:
        Complete HTML string ready for post-processing
    """
    template_path = TEMPLATES_DIR / "match3_moving.html"
    template = template_path.read_text(encoding='utf-8')
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    template = template.replace('var GOAL = 8;', f'var GOAL = {int(goal)};')

    if tile_data:
        tile_json = json.dumps(tile_data, separators=(',', ':'))
        template = template.replace('/*{{TILE_DATA}}*/null', tile_json)

    return template


def generate_mahjong_match(store_url: str, tile_data: list = None) -> str:
    """Generate a classic Mahjong solitaire (connect/pair-match) playable ad HTML.

    Mechanic: multi-layer stacked tile board; tap two identical FREE tiles to
    clear them (free = top uncovered AND a left/right side open); clear all
    tiles to win. Unicode mahjong glyph fallback when no tile_data; synth SFX,
    no embedded BGM.

    Args:
        store_url: App store URL for CTA
        tile_data: Optional list of base64 data URIs for tile face images (by type index)

    Returns:
        Complete HTML string ready for post-processing
    """
    template_path = TEMPLATES_DIR / "mahjong_match.html"
    template = template_path.read_text(encoding='utf-8')
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)

    if tile_data:
        tile_json = json.dumps(tile_data, separators=(',', ':'))
        template = template.replace('/*{{TILE_DATA}}*/null', tile_json)

    return template


def generate_find_differences(store_url: str, image_a: str, image_b: str, diffs: list) -> str:
    """Generate a classic Spot-the-Difference playable ad HTML.

    Mechanic: two near-identical images (A original, B altered) shown stacked;
    tap a difference spot to mark it; find all differences to win. Difference
    locations are supplied as normalized coordinates (x/y in 0..1 relative to
    image size, optional r hit-radius) since they cannot be auto-detected.

    Args:
        store_url: App store URL for CTA
        image_a: Data URI (base64) for the original image
        image_b: Data URI (base64) for the altered/difference image
        diffs: List of {"x":0..1, "y":0..1, "r":0..1?} normalized difference points

    Returns:
        Complete HTML string ready for post-processing
    """
    template_path = TEMPLATES_DIR / "find_differences.html"
    template = template_path.read_text(encoding='utf-8')
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    template = template.replace('/*{{IMG_A}}*/""', json.dumps(image_a))
    template = template.replace('/*{{IMG_B}}*/""', json.dumps(image_b))
    template = template.replace('/*{{DIFFS}}*/[]', json.dumps(diffs, separators=(',', ':')))
    return template


def compose_finddiff_from_levelpack(base_bytes: bytes, atlas_bytes: bytes, level: dict):
    """Build the A/B images + normalized diffs from a production level pack.

    Pack format (one complete set per level):
      - base image  : the scene WITHOUT differences (image A)
      - atlas image : sprite sheet holding the difference patches
      - level.json  : {"items": [{"pos":[x,y], "spr_uv":[ax,ay,ax2,ay2,dw,dh],
                       "cirPos":[cx,cy], "cir_size":diameter}, ...]}

    Image B is composed by cropping each patch from the atlas (ax,ay)-(ax2,ay2),
    scaling it to dw x dh, and pasting it onto a copy of the base at pos.
    Difference circles (cirPos + cir_size, in base pixels) are normalized to
    0..1 fractions for the template's hit-test.

    Returns (image_a_jpeg_bytes, image_b_jpeg_bytes, diffs_list).
    """
    from io import BytesIO
    from PIL import Image

    base = Image.open(BytesIO(base_bytes)).convert('RGBA')
    atlas = Image.open(BytesIO(atlas_bytes)).convert('RGBA')
    W, H = base.size

    items = level.get('items') or []
    if not items:
        raise ValueError("level.json 没有 items 数据。")

    img_b = base.copy()
    diffs = []
    avg = (W + H) / 2.0
    for it in items:
        uv = it.get('spr_uv')
        pos = it.get('pos')
        if uv and pos and len(uv) >= 6:
            ax, ay, ax2, ay2, dw, dh = uv[0], uv[1], uv[2], uv[3], int(uv[4]), int(uv[5])
            patch = atlas.crop((ax, ay, ax2, ay2))
            if (patch.width, patch.height) != (dw, dh):
                patch = patch.resize((dw, dh), Image.LANCZOS)
            # pos is the CENTER of the patch on the base image, not the top-left
            px = int(round(pos[0] - dw / 2.0))
            py = int(round(pos[1] - dh / 2.0))
            # paste with alpha mask (tolerates negative / off-canvas offsets)
            img_b.paste(patch, (px, py), patch)
        cir = it.get('cirPos')
        if cir:
            cx, cy = cir[0], cir[1]
            dia = it.get('cir_size', avg * 0.1)
            diffs.append({
                'x': round(cx / W, 4),
                'y': round(cy / H, 4),
                'r': round((dia / 2.0) / avg, 4),
            })

    if not diffs:
        raise ValueError("level.json 的 items 缺少 cirPos 坐标。")

    a_buf, b_buf = BytesIO(), BytesIO()
    base.convert('RGB').save(a_buf, format='JPEG', quality=90)
    img_b.convert('RGB').save(b_buf, format='JPEG', quality=90)
    return a_buf.getvalue(), b_buf.getvalue(), diffs


def generate_match3_drag(store_url: str, goal: int = 9, tile_data: list = None) -> str:
    """Generate a drag-to-arrange cabinet Match-3 playable ad HTML.

    Mechanic: left = single-column moving shelf, right = two fixed 2x6 shelves.
    Drag any tile into any empty cell; 3+ identical in a row/column clears. A
    clear inside the LEFT shelf starts its constant downward scroll (top-recycle
    refill); right-side clears do not move the left shelf. Win after `goal`
    clears. Emoji fallback; synth SFX, no embedded BGM. rAF + transform drag for
    smoothness.

    Args:
        store_url: App store URL for CTA
        goal: Number of clears to win
        tile_data: Optional list of base64 data URIs for tile images (by type index)

    Returns:
        Complete HTML string ready for post-processing
    """
    template_path = TEMPLATES_DIR / "match3_drag.html"
    template = template_path.read_text(encoding='utf-8')
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    template = template.replace('var GOAL = 8;', f'var GOAL = {int(goal)};')

    if tile_data:
        tile_json = json.dumps(tile_data, separators=(',', ':'))
        template = template.replace('/*{{TILE_DATA}}*/null', tile_json)

    return template


def generate_jigsaw_puzzle(store_url: str, rows: int = 4, cols: int = 6) -> str:
    """Generate a Jigsaw Puzzle playable ad HTML.

    The image is embedded via ASSET_MAIN_IMAGE_PLACEHOLDER by post_processor.

    Args:
        store_url: App store URL for CTA
        rows: Number of rows in the puzzle grid
        cols: Number of columns in the puzzle grid

    Returns:
        Complete HTML string ready for post-processing
    """
    template_path = TEMPLATES_DIR / "jigsaw_puzzle.html"
    template = template_path.read_text(encoding='utf-8')
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    return template


def generate_color_by_number(svg_content: str, store_url: str, num_blocks: int = 12) -> str:
    """Generate a complete Color-by-Number playable ad HTML from SVG region data.

    Args:
        svg_content: Raw SVG file content string
        store_url: App store URL for CTA
        num_blocks: Number of spatial blocks to divide the image into

    Returns:
        Complete HTML string ready for post-processing
    """
    data = parse_svg(svg_content, num_blocks=num_blocks)

    template_path = TEMPLATES_DIR / "color_by_number.html"
    template = template_path.read_text(encoding='utf-8')

    svg_paths_html = []
    for i, p in enumerate(data['paths']):
        svg_paths_html.append(
            f'<path data-idx="{i}" data-block="{p["blockIdx"]}" d="{p["d"]}"/>'
        )
    svg_paths_str = "\n".join(svg_paths_html)

    palette_html_parts = []
    unique_colors = []
    seen_hex = set()
    for p in data['palette']:
        if p['hex'] not in seen_hex:
            unique_colors.append(p['hex'])
            seen_hex.add(p['hex'])

    game_data = {
        'palette': [p['hex'] for p in data['palette']],
        'blocks': data['blocks'],
        'pathColors': [p['colorIdx'] for p in data['paths']],
    }

    template = template.replace('{{VIEWBOX}}', data['viewBox'])
    template = template.replace('{{SVG_PATHS}}', svg_paths_str)
    template = template.replace('{{NUM_BLOCKS}}', str(data['num_blocks']))
    template = template.replace('{{GAME_DATA_JSON}}', json.dumps(game_data, separators=(',', ':')))

    palette_btns = []
    for i in range(min(len(data['blocks']), num_blocks)):
        block_paths = data['blocks'][i]
        if block_paths:
            color_idx = data['paths'][block_paths[0]]['colorIdx']
            color = data['palette'][color_idx]['hex']
        else:
            color = '#ccc'
        palette_btns.append(
            f'<div class="color-btn" data-block="{i}" style="background:{color}">'
            f'<span class="num">{i+1}</span></div>'
        )
    template = template.replace('{{PALETTE_HTML}}', "\n".join(palette_btns))

    template = template.replace('STORE_URL_PLACEHOLDER', store_url)

    return template


_ARROW_DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # up,right,down,left
_ARROW_DIR_NAMES = {'up': 0, 'right': 1, 'down': 2, 'left': 3,
                    'u': 0, 'r': 1, 'd': 2, 'l': 3,
                    '0': 0, '1': 1, '2': 2, '3': 3}


def _arrow_norm_dir(d):
    if isinstance(d, int):
        return d % 4
    return _ARROW_DIR_NAMES.get(str(d).strip().lower(), 0)


def parse_unity_arrow_level(level_json, flip_y=True, drop_border=True):
    """Parse a Unity 'Arrows Escape' level export into (arrows, grid_n).

    Expected schema:
      {"FormationData":{"Width":W,"Height":H,...},
       "ArrowLineDatas":[{"Points":[{"x":..,"y":..}, ...]}, ...]}

    Each arrow's Points are its full per-cell polyline. Unity Points[0] is the
    arrow HEAD (fly-out end); the rest is the trailing tail. Unity uses y-up; the
    web board is y-down, so by default we flip y (y -> (H-1)-y) to match the
    editor view. Points are reversed so the template's path[-1] becomes the head.

    If `drop_border` is True (default), an arrow that traces (almost) the entire
    outer border frame is removed — these exporters sometimes add a decorative
    frame loop that is not a real playable arrow.

    Returns (arrows, n) ready for generate_arrow_puzzle(arrows=...).
    """
    if isinstance(level_json, (str, bytes)):
        level_json = json.loads(level_json)
    fd = level_json.get('FormationData', {})
    W = int(fd.get('Width', 20))
    H = int(fd.get('Height', 20))
    n = max(W, H)
    perimeter = 2 * (W + H) - 4

    def conv(p):
        x = int(p['x'])
        y = int(p['y'])
        if flip_y:
            y = (H - 1) - y
        return [x, y]

    arrows = []
    for a in level_json.get('ArrowLineDatas', []):
        raw = a.get('Points', [])
        if not raw:
            continue
        if drop_border and len(raw) >= perimeter * 0.7:
            on_border = sum(1 for p in raw
                            if int(p['x']) in (0, W - 1) or int(p['y']) in (0, H - 1))
            if on_border >= len(raw) * 0.95:
                continue  # decorative outer frame loop, skip
        pts = [conv(p) for p in raw]
        # reverse so path[-1] == Unity Points[0] (head); fly-out points away from tail
        pts = pts[::-1]
        if len(pts) >= 2:
            dx = pts[-1][0] - pts[-2][0]
            dy = pts[-1][1] - pts[-2][1]
            dx = (dx > 0) - (dx < 0)
            dy = (dy > 0) - (dy < 0)
            d = _ARROW_DIRS.index((dx, dy)) if (dx, dy) in _ARROW_DIRS else 1
        else:
            d = 1
        arrows.append({'path': pts, 'dir': d})
    return arrows, n


def _expand_orthogonal(p0, p1):
    """Yield cells stepping from p0 to p1 along a single row or column.

    Includes p1 but not p0. Raises if the move is not purely horizontal/vertical.
    """
    x0, y0 = p0
    x1, y1 = p1
    if x0 == x1 and y0 == y1:
        return []
    if x0 != x1 and y0 != y1:
        raise ValueError(f"路径段 {p0}->{p1} 不是水平或垂直方向，箭头轨迹只能正交移动。")
    cells = []
    if x0 == x1:
        step = 1 if y1 > y0 else -1
        for y in range(y0 + step, y1 + step, step):
            cells.append([x0, y])
    else:
        step = 1 if x1 > x0 else -1
        for x in range(x0 + step, x1 + step, step):
            cells.append([x, y0])
    return cells


def _trajectory_to_path(start, turns, end):
    """Expand start + turns + end into a per-cell path (start first)."""
    waypoints = [list(start)] + [list(t) for t in (turns or [])] + [list(end)]
    path = [list(waypoints[0])]
    for i in range(len(waypoints) - 1):
        for c in _expand_orthogonal(waypoints[i], waypoints[i + 1]):
            path.append(c)
    return path


def _simulate_clearable(arrows, n):
    """Greedy check matching the runtime mechanic.

    Each arrow's HEAD is path[-1]; it flies STRAIGHT along `dir` from the head to
    the board edge. It can be removed iff that straight line is free of every
    OTHER arrow's body cell (a body cell = any cell of that arrow's path).
    Returns True if all arrows can be removed in some order.
    """
    DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    # body cells -> owning index
    body = {}
    heads = {}
    dirs = {}
    for i, a in enumerate(arrows):
        path = a['path']
        heads[i] = (path[-1][0], path[-1][1])
        dirs[i] = a['dir']
        for c in path:
            body[(c[0], c[1])] = i  # last writer wins; overlaps rare/ok for check

    # rebuild per-arrow body sets so removal clears all its cells
    bodysets = []
    for a in arrows:
        bodysets.append(set((c[0], c[1]) for c in a['path']))
    occ = {}
    for i, bs in enumerate(bodysets):
        for c in bs:
            occ.setdefault(c, set()).add(i)

    removed = set()
    changed = True
    while changed and len(removed) < len(arrows):
        changed = False
        for i, a in enumerate(arrows):
            if i in removed:
                continue
            hx, hy = heads[i]
            dx, dy = DIRS[dirs[i]]
            x, y = hx + dx, hy + dy
            clear = True
            while 0 <= x < n and 0 <= y < n:
                owners = occ.get((x, y))
                if owners and any(o != i and o not in removed for o in owners):
                    clear = False
                    break
                x += dx
                y += dy
            if clear:
                for c in bodysets[i]:
                    if (c in occ):
                        occ[c].discard(i)
                removed.add(i)
                changed = True
    return len(removed) == len(arrows)


def generate_arrow_puzzle(store_url: str, n: int = 20, count: int = None, lives: int = 5,
                          seed: int = None, arrows: list = None,
                          shape: list = None, grid_size=None, curvy: bool = False,
                          max_len: int = 6, max_turns: int = 2,
                          parallel: bool = False, lanes: int = 6, gap: int = 1) -> str:
    """Generate an Arrows-Escape playable ad HTML.

    Mechanic (real "Arrows Puzzle Escape" / com.ecffri.arrows): a point grid of
    plain black arrows. Each arrow sits on its START cell. Tapping it sends it
    sliding along its TRAJECTORY (which may turn) and off the screen — but only
    if that whole trajectory is currently free of other arrows. If something is
    in the way it crashes into it, stops, and the player loses a life. Clear all
    arrows to win; run out of lives to lose. Levels are chains: only the arrow
    whose trajectory is currently clear can leave, freeing the next.

    Input modes (checked in order):
      - arrows (trajectory form): list of
          {"start":[x,y], "turns":[[x,y],...], "end":[x,y], "final_direction":"UP"}
        Each is expanded to a per-cell path (start..turns..end) plus the fly-out
        direction. Grid auto-sizes to fit. Solvability is validated (warns if not).
      - arrows (simple form): list of {"x","y","dir"} -> single-cell arrows.
      - shape: list of [x,y] allowed cells -> a solvable single-cell chain is
        auto-built covering exactly those cells.
      - (none): random medium-density board.

    Args:
        store_url: App store URL for CTA
        n: Default grid size (auto-grows to fit any coordinates)
        count: Arrow count for random mode
        lives: Starting lives
        seed: RNG seed
        arrows: Custom layout (trajectory form or simple form)
        shape: Allowed cells [[x,y],...] for auto chain generation
        grid_size: Optional [w,h] / int; max dimension used as n (auto-grow still applies)

    Returns:
        Complete HTML string ready for post-processing
    """
    def emit(level):
        template_path = TEMPLATES_DIR / "arrow_puzzle.html"
        template = template_path.read_text(encoding='utf-8')
        template = template.replace('STORE_URL_PLACEHOLDER', store_url)
        template = template.replace('/*{{LEVEL_DATA}}*/null', json.dumps(level, separators=(',', ':')))
        return template

    if grid_size is not None:
        if isinstance(grid_size, (list, tuple)) and grid_size:
            n = max(int(grid_size[0]), int(grid_size[-1]))
        else:
            n = int(grid_size)
    n = max(4, min(int(n), 100))

    # ---- mode: explicit arrows ----
    if arrows:
        first = arrows[0]
        is_path = isinstance(first, dict) and 'path' in first
        is_traj = isinstance(first, dict) and ('start' in first or 'end' in first)
        out = []
        seen_heads = set()
        mx = 0
        if is_path:
            # already-expanded per-cell paths: [{'path':[[x,y],...], 'dir':int|name}]
            for a in arrows:
                pts = a.get('path') or []
                if not pts:
                    continue
                pts = [[int(c[0]), int(c[1])] for c in pts]
                head = (pts[0][0], pts[0][1])
                if head in seen_heads:
                    continue
                seen_heads.add(head)
                if 'dir' in a:
                    fd = _arrow_norm_dir(a['dir'])
                elif len(pts) >= 2:
                    dx = pts[-1][0] - pts[-2][0]
                    dy = pts[-1][1] - pts[-2][1]
                    dx = (dx > 0) - (dx < 0)
                    dy = (dy > 0) - (dy < 0)
                    fd = _ARROW_DIRS.index((dx, dy)) if (dx, dy) in _ARROW_DIRS else 1
                else:
                    fd = 1
                out.append({'path': pts, 'dir': fd})
                for c in pts:
                    mx = max(mx, c[0], c[1])
        elif is_traj:
            for a in arrows:
                start = a.get('start')
                end = a.get('end', start)
                if not start:
                    continue
                path = _trajectory_to_path(start, a.get('turns'), end)
                head = (path[0][0], path[0][1])
                if head in seen_heads:
                    continue
                seen_heads.add(head)
                fd = a.get('final_direction', a.get('dir', 'up'))
                out.append({'path': path, 'dir': _arrow_norm_dir(fd)})
                for c in path:
                    mx = max(mx, c[0], c[1])
        else:
            for a in arrows:
                try:
                    x = int(a['x']); y = int(a['y'])
                except (KeyError, TypeError, ValueError):
                    continue
                if x < 0 or y < 0 or (x, y) in seen_heads:
                    continue
                seen_heads.add((x, y))
                out.append({'path': [[x, y]], 'dir': _arrow_norm_dir(a.get('dir', 'up'))})
                mx = max(mx, x, y)
        if not out:
            raise ValueError("自定义 arrows 为空或无效。")
        gn = min(max(n, mx + 1), 100)
        return emit({'n': gn, 'lives': int(lives), 'arrows': out,
                     'solvable': _simulate_clearable(out, gn)})

    # ---- mode: shape cells -> auto solvable single-cell chain ----
    if shape:
        cells = []
        seen = set()
        mx = 0
        for c in shape:
            try:
                x = int(c[0]); y = int(c[1])
            except (TypeError, ValueError, IndexError, KeyError):
                continue
            if x < 0 or y < 0 or (x, y) in seen:
                continue
            seen.add((x, y))
            cells.append((x, y))
            mx = max(mx, x, y)
        if not cells:
            raise ValueError("shape 为空或无效（需为 [[x,y],...]）。")
        gn = min(max(n, mx + 1), 100)
        cellset = set(cells)

        def try_build(r):
            occupied = {}
            remaining = set(cellset)
            placed = []

            def clear_to_edge(x, y, di):
                dx, dy = _ARROW_DIRS[di]
                cx, cy = x + dx, y + dy
                while 0 <= cx < gn and 0 <= cy < gn:
                    if (cx, cy) in occupied:
                        return False
                    cx += dx
                    cy += dy
                return True

            while remaining:
                cand = []
                for (x, y) in remaining:
                    ok = [di for di in range(4) if clear_to_edge(x, y, di)]
                    if ok:
                        cand.append((x, y, ok))
                if not cand:
                    return None
                minopt = min(len(c[2]) for c in cand)
                pool = [c for c in cand if len(c[2]) == minopt]
                x, y, ok = r.choice(pool)
                di = r.choice(ok)
                occupied[(x, y)] = di
                placed.append({'path': [[x, y]], 'dir': di})
                remaining.discard((x, y))
            return placed

        placed = None
        for attempt in range(80):
            placed = try_build(random.Random((seed or 0) * 100 + attempt))
            if placed and len(placed) == len(cellset):
                break
            placed = None
        if not placed:
            raise ValueError("无法在该 shape 上生成完全覆盖的可解关卡。")
        return emit({'n': gn, 'lives': int(lives), 'arrows': placed, 'solvable': True})

    # ---- mode: parallel pipes (equidistant, non-crossing, can turn together) ----
    if parallel:
        rng = random.Random(seed)
        n = max(8, min(int(n), 60))
        g = max(1, int(gap)) + 1  # center-to-center spacing between lanes (>=2 so they never touch)
        lanes = max(2, int(lanes))

        # A "rail" is a turning polyline of unit steps. We build ONE base rail as a
        # sequence of directions, then create `lanes` copies each shifted by a fixed
        # perpendicular offset. Parallel offset copies of the same shape never cross
        # and stay equidistant by construction. Each lane exits off the board.
        # Choose a primary axis: horizontal lanes stacked vertically, or vice versa.
        horizontal = rng.random() < 0.5

        # base rail directions: mostly forward with a couple of synchronized jogs
        # forward axis dir index, lateral dir index
        if horizontal:
            fwd, lat = 1, 2          # move right, lanes stacked downward
        else:
            fwd, lat = 2, 1          # move down, lanes stacked rightward

        # forward axis dir index, lateral (lane-stacking) dir index
        if horizontal:
            fwd, lat = 1, 2          # move right, lanes stacked downward
        else:
            fwd, lat = 2, 1          # move down, lanes stacked rightward

        # build base path of forward length L with up to max_turns synchronized
        # jogs. A jog shifts the WHOLE bundle along the forward-perpendicular axis;
        # to avoid lanes overlapping each other, every lane performs the identical
        # jog, and the jog axis is the SAME as the lane-stacking axis, so the whole
        # bundle slides as a rigid body (spacing preserved, no crossings).
        # Straight parallel lanes: every lane is a straight rail along the forward
        # axis, lanes stacked equidistantly along the lateral axis. Straight parallel
        # lines are guaranteed equidistant and never cross. Each lane runs the full
        # board span and flies out the forward edge.
        ldx, ldy = _ARROW_DIRS[lat]
        fdx, fdy = _ARROW_DIRS[fwd]
        if horizontal:
            sx0, sy0 = 0, max(0, (n - (lanes - 1) * g) // 2)
            span = n
        else:
            sx0, sy0 = max(0, (n - (lanes - 1) * g) // 2), 0
            span = n

        # vary lane lengths a bit so the bundle isn't a perfect rectangle (still
        # parallel & non-crossing because each stays on its own row/column)
        placed = []
        for li in range(lanes):
            sx = sx0 + ldx * (li * g)
            sy = sy0 + ldy * (li * g)
            length = rng.randint(max(3, span // 2), span)  # cells in this lane
            path = [[sx, sy]]
            x, y = sx, sy
            for _ in range(length - 1):
                nx, ny = x + fdx, y + fdy
                if nx < 0 or nx >= n or ny < 0 or ny >= n:
                    break
                x, y = nx, ny
                path.append([x, y])
            placed.append({'path': path, 'dir': fwd})

        solvable = _simulate_clearable(placed, n)
        return emit({'n': n, 'lives': int(lives), 'arrows': placed, 'solvable': solvable})

    # ---- mode: random ----
    rng = random.Random(seed)
    n = max(6, min(int(n), 40 if curvy else 24))
    total = n * n
    if count is None:
        count = max(12, int(round(total * (0.05 if curvy else 0.07))))
    count = min(count, total)
    occupied = {}  # start cells of arrows already placed (these will be cleared FIRST)

    def clear_edge(x, y, di):
        dx, dy = _ARROW_DIRS[di]
        cx, cy = x + dx, y + dy
        while 0 <= cx < n and 0 <= cy < n:
            if (cx, cy) in occupied:
                return False
            cx += dx
            cy += dy
        return True

    if not curvy:
        free = [(x, y) for y in range(n) for x in range(n)]
        rng.shuffle(free)
        placed = []
        for (x, y) in free:
            if len(placed) >= count:
                break
            dorder = [0, 1, 2, 3]
            rng.shuffle(dorder)
            ch = None
            for di in dorder:
                if clear_edge(x, y, di):
                    ch = di
                    break
            if ch is None:
                continue
            occupied[(x, y)] = ch
            placed.append({'path': [[x, y]], 'dir': ch})
        return emit({'n': n, 'lives': int(lives), 'arrows': placed, 'solvable': True})

    # ---- curvy random: turning, variable-length trajectories ----
    # Reverse construction: arrows placed earlier are cleared FIRST. A new arrow's
    # whole trajectory must avoid the start cells of ALREADY-placed arrows (they
    # fly out before this one, so at this arrow's turn the board only still holds
    # arrows placed AFTER it — whose starts are not yet in `occupied`). Walking a
    # turning path off the board, blocked only by `occupied`, guarantees the
    # reverse order is a valid clearing sequence.
    def walk_curvy(sx, sy):
        # returns (path_cells_including_start, final_dir) or None
        dirs = [0, 1, 2, 3]
        rng.shuffle(dirs)
        for first in dirs:
            path = [(sx, sy)]
            visited = {(sx, sy)}
            x, y = sx, sy
            d = first
            turns_left = rng.randint(0, max_turns)
            steps_left = rng.randint(2, max_len)
            ok = True
            dead = False
            while True:
                dx, dy = _ARROW_DIRS[d]
                nx, ny = x + dx, y + dy
                # off board in current dir -> success (flew out)
                if not (0 <= nx < n and 0 <= ny < n):
                    return [list(c) for c in path], d
                if (nx, ny) in occupied or (nx, ny) in visited:
                    # try a turn instead of advancing, if allowed
                    if turns_left > 0:
                        turned = False
                        for nd in ([1, 3] if d in (0, 2) else [0, 2]):
                            tdx, tdy = _ARROW_DIRS[nd]
                            tx, ty = x + tdx, y + tdy
                            if (0 <= tx < n and 0 <= ty < n) and (tx, ty) not in occupied and (tx, ty) not in visited:
                                d = nd
                                turns_left -= 1
                                turned = True
                                break
                            if not (0 <= tx < n and 0 <= ty < n):
                                # turning leads straight off board: fly out now
                                return [list(c) for c in path], nd
                        if turned:
                            continue
                    dead = True
                    break
                # advance
                x, y = nx, ny
                path.append((x, y))
                visited.add((x, y))
                steps_left -= 1
                if steps_left <= 0 and turns_left > 0 and rng.random() < 0.6:
                    # opportunistic turn to add a bend
                    for nd in ([1, 3] if d in (0, 2) else [0, 2]):
                        tdx, tdy = _ARROW_DIRS[nd]
                        tx, ty = x + tdx, y + tdy
                        if not (0 <= tx < n and 0 <= ty < n):
                            return [list(c) for c in path], nd
                        if (tx, ty) not in occupied and (tx, ty) not in visited:
                            d = nd
                            turns_left -= 1
                            steps_left = rng.randint(1, max_len)
                            break
            if dead:
                continue
        return None

    free = [(x, y) for y in range(n) for x in range(n)]
    rng.shuffle(free)
    placed = []
    for (x, y) in free:
        if len(placed) >= count:
            break
        if (x, y) in occupied:
            continue
        res = walk_curvy(x, y)
        if res is None:
            continue
        path, fdir = res
        occupied[(x, y)] = fdir
        placed.append({'path': path, 'dir': fdir})
    return emit({'n': n, 'lives': int(lives), 'arrows': placed,
                 'solvable': _simulate_clearable(placed, n)})



# ===== JigSolitaire (拼图纸牌) templates =====
# Each template HTML lives in templates/jig_*.html with placeholders:
#   PUZZLE_IMAGE_PLACEHOLDER  - a base64 data URI for the puzzle picture
#   PUZZLE_VIDEO_PLACEHOLDER  - a base64 data URI for the intro/loop video
#   STORE_URL_PLACEHOLDER     - the app store CTA url

def generate_jig_core(store_url: str, image_data_uri: str) -> str:
    """Core gameplay jigsaw (retro): user uploads ONE image. 4x4 swap puzzle."""
    template = (TEMPLATES_DIR / "jig_core.html").read_text(encoding='utf-8')
    template = template.replace('PUZZLE_IMAGE_PLACEHOLDER', image_data_uri)
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    return template


def generate_jig_irregular(store_url: str, image_data_uri: str) -> str:
    """Irregular interlocking pieces jigsaw: user uploads ONE image. 24 SVG clip-path pieces."""
    template = (TEMPLATES_DIR / "jig_irregular.html").read_text(encoding='utf-8')
    template = template.replace('PUZZLE_IMAGE_PLACEHOLDER', image_data_uri)
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    return template


def generate_jig_video_core(store_url: str, video_data_uri: str) -> str:
    """Intro video + core gameplay: user uploads a video (puzzle image derived from last frame)."""
    template = (TEMPLATES_DIR / "jig_video_core.html").read_text(encoding='utf-8')
    template = template.replace('PUZZLE_VIDEO_PLACEHOLDER', video_data_uri)
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    return template


def generate_jig_video_only(store_url: str, video_data_uri: str) -> str:
    """Solve while a video plays: user uploads ONE video; tiles share live video frames."""
    template = (TEMPLATES_DIR / "jig_video_only.html").read_text(encoding='utf-8')
    template = template.replace('PUZZLE_VIDEO_PLACEHOLDER', video_data_uri)
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    return template


def generate_water_sort(store_url: str, colors: int = 6, empty: int = 2, cap: int = 4, seed: int = None) -> str:
    """Generate a Water Sort puzzle playable ad HTML (deterministic, no API key).

    Rules: each tube holds up to `cap` color segments. Pour the top run of one
    tube onto another only if the target is empty or its top color matches. Win
    when every tube is a single solid color (or empty).

    Solvability is guaranteed by: build the solved state (each color fills one
    tube), shuffle all segments across the color tubes, add `empty` empty tubes,
    then VERIFY with a DFS solver; retry until a solvable layout is found.

    Args:
        store_url: App store URL for CTA
        colors: number of distinct colors (= number of filled tubes)
        empty: number of empty helper tubes
        cap: tube capacity (segments per tube)
        seed: optional RNG seed

    Returns:
        Complete HTML string ready for post-processing
    """
    rng = random.Random(seed)
    colors = max(3, min(int(colors), 9))
    cap = max(3, min(int(cap), 6))
    empty = max(1, min(int(empty), 4))

    PALETTE = ['#ff5d5d', '#5db0ff', '#ffd14d', '#5de8a0', '#c08bff',
               '#ff9ec7', '#ffa552', '#7fe9ff', '#b6d94d']

    def solved_state():
        return tuple(tuple([c] * cap) for c in range(colors)) + tuple(() for _ in range(empty))

    def is_solved(state):
        for t in state:
            if len(t) == 0:
                continue
            if len(t) != cap or any(x != t[0] for x in t):
                return False
        return True

    def legal_moves(state):
        n = len(state)
        mv = []
        for a in range(n):
            A = state[a]
            if not A:
                continue
            # top run
            c = A[-1]
            run = 0
            for i in range(len(A) - 1, -1, -1):
                if A[i] == c:
                    run += 1
                else:
                    break
            # skip pouring from an already-finished tube
            if len(A) == cap and run == cap:
                continue
            for b in range(n):
                if a == b:
                    continue
                B = state[b]
                if len(B) >= cap:
                    continue
                if len(B) == 0 or B[-1] == c:
                    mv.append((a, b, min(run, cap - len(B))))
        return mv

    def apply_move(state, mv):
        a, b, k = mv
        s = [list(t) for t in state]
        c = s[a][-1]
        for _ in range(k):
            s[a].pop()
            s[b].append(c)
        return tuple(tuple(t) for t in s)

    def solvable(start, max_states=200000):
        seen = set()
        stack = [start]
        seen.add(start)
        cnt = 0
        while stack:
            st = stack.pop()
            cnt += 1
            if cnt > max_states:
                return False
            if is_solved(st):
                return True
            for mv in legal_moves(st):
                ns = apply_move(st, mv)
                if ns not in seen:
                    seen.add(ns)
                    stack.append(ns)
        return False

    def make_layout():
        # all segments = colors x cap, shuffled into the color tubes
        segs = []
        for c in range(colors):
            segs += [c] * cap
        rng.shuffle(segs)
        tubes = []
        idx = 0
        for _ in range(colors):
            tubes.append(segs[idx:idx + cap])
            idx += cap
        for _ in range(empty):
            tubes.append([])
        return tubes

    layout = None
    for _ in range(400):
        cand = make_layout()
        start = tuple(tuple(t) for t in cand)
        # reject already-solved or trivially-near-solved layouts
        if is_solved(start):
            continue
        if solvable(start):
            layout = cand
            break
    if layout is None:
        # extremely unlikely fallback: solved state lightly perturbed
        layout = make_layout()

    level = {
        'cap': cap,
        'colors': PALETTE[:colors],
        'tubes': layout,
    }

    template_path = TEMPLATES_DIR / "water_sort.html"
    template = template_path.read_text(encoding='utf-8')
    template = template.replace('STORE_URL_PLACEHOLDER', store_url)
    template = template.replace('/*{{LEVEL_DATA}}*/null', json.dumps(level, separators=(',', ':')))
    return template
