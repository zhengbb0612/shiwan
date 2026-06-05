import re
import math
import xml.etree.ElementTree as ET
from collections import defaultdict


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_path_center(d: str) -> tuple:
    """Extract approximate center point from SVG path data by averaging all coordinate pairs."""
    nums = re.findall(r'[-+]?[0-9]*\.?[0-9]+', d)
    if len(nums) < 2:
        return (1024, 1024)
    xs, ys = [], []
    for i in range(0, min(len(nums), 40), 2):
        try:
            x, y = float(nums[i]), float(nums[i + 1])
            if 0 <= x <= 4096 and 0 <= y <= 4096:
                xs.append(x)
                ys.append(y)
        except (ValueError, IndexError):
            continue
    if not xs:
        return (1024, 1024)
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def assign_spatial_blocks(paths_with_info: list, num_blocks: int = 12) -> list:
    """Divide paths into spatial blocks using quantile-based grid for even distribution.

    Returns list of blocks, each containing path indices.
    """
    if not paths_with_info:
        return []

    cols = int(math.ceil(math.sqrt(num_blocks)))
    rows = int(math.ceil(num_blocks / cols))

    xs = sorted(set(p['center'][0] for p in paths_with_info))
    ys = sorted(set(p['center'][1] for p in paths_with_info))

    def quantile_cuts(values, n):
        if len(values) <= n:
            return values + [values[-1] + 1]
        step = len(values) / n
        cuts = [values[min(int(i * step), len(values) - 1)] for i in range(n)]
        cuts.append(values[-1] + 1)
        return cuts

    x_cuts = quantile_cuts(xs, cols)
    y_cuts = quantile_cuts(ys, rows)

    def get_block(cx, cy):
        col = 0
        for i in range(len(x_cuts) - 1):
            if cx >= x_cuts[i]:
                col = i
        row = 0
        for i in range(len(y_cuts) - 1):
            if cy >= y_cuts[i]:
                row = i
        return row * cols + col

    blocks = defaultdict(list)
    for i, p in enumerate(paths_with_info):
        block_id = get_block(p['center'][0], p['center'][1])
        blocks[block_id].append(i)

    result = []
    for block_id in sorted(blocks.keys()):
        if blocks[block_id]:
            result.append(blocks[block_id])

    while len(result) > num_blocks:
        smallest = min(range(len(result)), key=lambda i: len(result[i]))
        items = result.pop(smallest)
        nearest = min(range(len(result)), key=lambda i: len(result[i]))
        result[nearest].extend(items)

    max_per_block = len(paths_with_info) // num_blocks * 3
    final = []
    for block in result:
        if len(block) > max_per_block and len(final) < num_blocks:
            mid = len(block) // 2
            final.append(block[:mid])
            final.append(block[mid:])
        else:
            final.append(block)

    while len(final) > num_blocks:
        smallest = min(range(len(final)), key=lambda i: len(final[i]))
        items = final.pop(smallest)
        nearest = min(range(len(final)), key=lambda i: len(final[i]))
        final[nearest].extend(items)

    return final


def parse_svg(svg_content: str, num_blocks: int = 12) -> dict:
    """Parse SVG region file, keep all colors, and divide into spatial blocks.

    Returns:
        {
            "viewBox": "0 0 2048 2048",
            "palette": [{"class": "st0", "hex": "#32292B"}, ...],
            "paths": [{"d": "M...", "colorIdx": 0, "blockIdx": 0}, ...],
            "blocks": [[0,1,2,...], [3,4,5,...], ...],
            "total_paths": 467,
            "num_colors": 22,
            "num_blocks": 12
        }
    """
    root = ET.fromstring(svg_content)

    viewbox = root.get('viewBox', '0 0 2048 2048')

    style_el = root.find('.//{http://www.w3.org/2000/svg}style')
    if style_el is None:
        style_el = root.find('.//style')
    style_text = style_el.text if style_el is not None else ''

    class_to_color = {}
    for match in re.finditer(r'\.(st\d+)\s*\{\s*fill\s*:\s*(#[0-9A-Fa-f]{6})\s*;?\s*\}', style_text):
        class_to_color[match.group(1)] = match.group(2)

    palette = []
    color_to_idx = {}
    for cls, hex_color in class_to_color.items():
        idx = len(palette)
        palette.append({'class': cls, 'hex': hex_color})
        color_to_idx[cls] = idx

    all_path_els = root.findall('.//{http://www.w3.org/2000/svg}path')
    if not all_path_els:
        all_path_els = root.findall('.//path')

    paths_info = []
    for path_el in all_path_els:
        cls = path_el.get('class', '').strip()
        d = path_el.get('d', '').strip()
        if cls and d and cls in color_to_idx:
            center = get_path_center(d)
            paths_info.append({
                'd': d,
                'colorIdx': color_to_idx[cls],
                'center': center,
            })

    blocks = assign_spatial_blocks(paths_info, num_blocks=num_blocks)

    for block_idx, path_indices in enumerate(blocks):
        for pi in path_indices:
            paths_info[pi]['blockIdx'] = block_idx

    paths_out = [{'d': p['d'], 'colorIdx': p['colorIdx'], 'blockIdx': p['blockIdx']} for p in paths_info]

    return {
        'viewBox': viewbox,
        'palette': palette,
        'paths': paths_out,
        'blocks': blocks,
        'total_paths': len(paths_out),
        'num_colors': len(palette),
        'num_blocks': len(blocks),
    }


def detect_region_svg(file_content: bytes, filename: str) -> bool:
    """Check if an uploaded file is a region SVG (has styled paths with fill colors)."""
    if not filename.lower().endswith('.svg'):
        return False
    try:
        text = file_content.decode('utf-8', errors='ignore')
        has_style_fills = bool(re.search(r'\.st\d+\s*\{\s*fill\s*:', text))
        has_paths = '<path' in text
        return has_style_fills and has_paths
    except Exception:
        return False
