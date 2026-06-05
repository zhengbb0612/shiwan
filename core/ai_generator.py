import os
import re
from pathlib import Path

ssl_cert = os.environ.get("SSL_CERT_FILE", "")
if ssl_cert and not os.path.exists(ssl_cert):
    fixed = ssl_cert.replace("miniconda3/ssl/", "miniconda3/Library/ssl/").replace("miniconda3\\ssl\\", "miniconda3\\Library\\ssl\\")
    if os.path.exists(fixed):
        os.environ["SSL_CERT_FILE"] = fixed
    else:
        os.environ.pop("SSL_CERT_FILE", None)

from anthropic import Anthropic

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_system_prompt() -> str:
    return (PROMPTS_DIR / "system_prompt.md").read_text(encoding="utf-8")


def load_channel_specs() -> str:
    return (PROMPTS_DIR / "channel_specs.md").read_text(encoding="utf-8")


def build_user_message(gameplay_desc: str, store_url: str, reference_html: str = None, has_main_image: bool = False) -> str:
    parts = []
    parts.append(f"## Game Description\n\n{gameplay_desc}")
    parts.append(f"\n## Store URL\n\n{store_url}")

    if has_main_image:
        parts.append("""
## User-Provided Image Asset (IMPORTANT)

The user has uploaded a main image. You MUST use it in the game by placing the exact placeholder string `ASSET_MAIN_IMAGE_PLACEHOLDER` as the image source. The post-processor will replace it with the actual base64 image.

For puzzle/jigsaw games: Use the image as the puzzle picture. Set it as CSS background-image on each tile:
```css
:root { --puzzle-img: url(ASSET_MAIN_IMAGE_PLACEHOLDER); }
.tile { background-image: var(--puzzle-img); background-size: 400% 400%; }
```
Each tile uses `background-position` to show its portion of the full image.

For coloring games: Use it as the base reference image displayed as a preview.
For hidden object: Use it as the scene background.
For spot-the-difference: Use it as one of the comparison images.

DO NOT draw your own graphics when the user provides an image. USE THE PLACEHOLDER.""")

    if reference_html:
        truncated = reference_html[:80000]
        parts.append(f"\n## Reference Playable Ad Code (analyze structure and mechanics)\n\n```html\n{truncated}\n```")

    parts.append("\n## Task\n\nGenerate a complete, self-contained HTML playable ad based on the game description above. Follow all specifications from the system prompt. Output ONLY the HTML code.")

    return "\n".join(parts)


def extract_html_from_response(response_text: str) -> str:
    html_match = re.search(r'(<!DOCTYPE html>.*?</html>)', response_text, re.DOTALL | re.IGNORECASE)
    if html_match:
        return html_match.group(1)

    if response_text.strip().startswith('<!DOCTYPE') or response_text.strip().startswith('<html'):
        return response_text.strip()

    code_match = re.search(r'```html\s*(.*?)\s*```', response_text, re.DOTALL)
    if code_match:
        return code_match.group(1)

    return response_text.strip()


class PlayableAdGenerator:
    def __init__(self, api_key: str, model: str = "ppio/pa/claude-sonnet-4-6", base_url: str = None):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        elif os.environ.get("ANTHROPIC_BASE_URL"):
            kwargs["base_url"] = os.environ["ANTHROPIC_BASE_URL"]
        self.client = Anthropic(**kwargs)
        self.model = model
        self.system_prompt = load_system_prompt()
        self.channel_specs = load_channel_specs()

    def generate(self, gameplay_desc: str, store_url: str, reference_html: str = None,
                 has_main_image: bool = False, on_token=None) -> str:
        system = self.system_prompt + "\n\n---\n\n" + self.channel_specs
        user_message = build_user_message(gameplay_desc, store_url, reference_html, has_main_image)

        if on_token:
            collected = []
            with self.client.messages.stream(
                model=self.model,
                max_tokens=32000,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                for text in stream.text_stream:
                    collected.append(text)
                    on_token(text)
            full_response = "".join(collected)
        else:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=32000,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            full_response = response.content[0].text

        return extract_html_from_response(full_response)
