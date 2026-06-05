import re
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

from .channels import CHANNELS
from .media import compress_image, make_data_uri_from_bytes, make_data_uri, process_asset


def validate_js_syntax(html: str) -> tuple[bool, str]:
    js_match = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
    if not js_match:
        return True, ""
    js_code = js_match.group(1)
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(js_code)
            tmp_path = f.name
        result = subprocess.run(
            ['node', '--check', tmp_path],
            capture_output=True, text=True, timeout=5
        )
        Path(tmp_path).unlink(missing_ok=True)
        if result.returncode != 0:
            return False, result.stderr
        return True, ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True, ""


def adapt_for_channel(html: str, channel: str, store_url: str) -> str:
    config = CHANNELS[channel]

    html = html.replace('STORE_URL_PLACEHOLDER', store_url)

    original_open_store = re.search(
        r'(  function openStore\(\) \{.*?\n  \})',
        html,
        re.DOTALL
    )
    if original_open_store:
        html = html.replace(original_open_store.group(1), config['open_store'])

    if config['extra_meta']:
        html = html.replace('<!-- UAC_META_PLACEHOLDER -->', config['extra_meta'])
    else:
        html = html.replace('<!-- UAC_META_PLACEHOLDER -->', '')

    return html


def embed_image(html: str, image_data: bytes, placeholder: str = 'ASSET_MAIN_IMAGE_PLACEHOLDER', filename: str = '') -> str:
    data_uri, _, _ = process_asset(image_data, filename)
    return html.replace(placeholder, data_uri)


def embed_audio(html: str, audio_data: bytes, mime_type: str, placeholder: str) -> str:
    from .media import bytes_to_base64
    b64 = bytes_to_base64(audio_data)
    data_uri = f"data:{mime_type};base64,{b64}"
    return html.replace(placeholder, data_uri)


def check_file_size(html: str, max_mb: float) -> tuple[bool, float]:
    size_mb = len(html.encode('utf-8')) / 1024 / 1024
    return size_mb <= max_mb, size_mb


def process_all_channels(html: str, store_url: str, assets: dict = None, output_dir: str = None) -> dict:
    results = {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "output"

    output_dir = Path(output_dir)

    js_valid, js_error = validate_js_syntax(html)

    for channel_key, config in CHANNELS.items():
        channel_html = adapt_for_channel(html, channel_key, store_url)

        if assets:
            if 'main_image' in assets and assets['main_image']:
                channel_html = embed_image(channel_html, assets['main_image'],
                                           filename=assets.get('main_image_name', ''))
            if 'bg_image' in assets and assets['bg_image']:
                channel_html = embed_image(channel_html, assets['bg_image'], 'ASSET_BG_IMAGE_PLACEHOLDER',
                                           filename=assets.get('bg_image_name', ''))

        ok, size_mb = check_file_size(channel_html, config['max_size_mb'])

        channel_dir = output_dir / config['name']
        channel_dir.mkdir(parents=True, exist_ok=True)

        filename = f"playable_{channel_key}_{timestamp}.html"
        filepath = channel_dir / filename

        filepath.write_text(channel_html, encoding='utf-8')

        results[channel_key] = {
            'path': str(filepath),
            'size_mb': size_mb,
            'within_limit': ok,
            'max_mb': config['max_size_mb'],
            'html': channel_html,
            'js_valid': js_valid,
            'js_error': js_error,
        }

    return results
