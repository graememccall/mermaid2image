#!/usr/bin/env python3
"""
mermaid2image.py

Scans Markdown (.md) files for Mermaid diagrams and renders each one to a
PNG image using the mermaid.ink rendering service.

Usage:
    python mermaid2image.py [path] [-o OUTPUT_DIR] [-t {png,svg}]

    path        A markdown file or a directory containing markdown files.
                Defaults to the current directory.
    -o/--output Directory to write images to. Defaults to "./output".
    -t/--type   Image type to request: "png" (default) or "svg".

A markdown file may contain diagrams either:
  * fenced in ```mermaid ... ``` code blocks, or
  * as the entire file content (no fences), e.g. starting with
    "flowchart", "sequenceDiagram", "classDiagram", etc.
"""

import argparse
import base64
import json
import re
import sys
import time
import zlib
from pathlib import Path

import requests

# Keywords that identify a chunk of text as a Mermaid diagram when there
# are no ```mermaid fences in the file.
MERMAID_KEYWORDS = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "gantt",
    "pie",
    "journey",
    "mindmap",
    "timeline",
    "gitGraph",
    "quadrantChart",
    "requirementDiagram",
    "C4Context",
    "sankey-beta",
)

FENCE_RE = re.compile(r"```(?:mermaid)\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_diagrams(text: str) -> list[str]:
    """Return a list of Mermaid diagram source strings found in `text`."""
    diagrams = [m.group(1).strip() for m in FENCE_RE.finditer(text)]
    if diagrams:
        return diagrams

    stripped = text.strip()
    if stripped and stripped.split(None, 1)[0].rstrip(":") in MERMAID_KEYWORDS:
        return [stripped]
    # Also allow keyword to appear as first line without needing exact token
    first_line = stripped.splitlines()[0] if stripped else ""
    if any(first_line.strip().startswith(kw) for kw in MERMAID_KEYWORDS):
        return [stripped]

    return []


def mermaid_to_pako(diagram: str) -> str:
    """Encode a mermaid diagram the way mermaid.live/mermaid.ink expect:
    zlib-deflate the JSON state, then base64url-encode it, prefixed with
    'pako:'.
    """
    state = {
        "code": diagram,
        "mermaid": {"theme": "default"},
    }
    payload = json.dumps(state).encode("utf-8")
    compressed = zlib.compress(payload, level=9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return f"pako:{encoded}"


def render_diagram(
    diagram: str,
    image_type: str = "png",
    timeout: int = 30,
    width: int = 1200,
    scale: float = 3,
    bg_color: str = "!white",
) -> bytes:
    """Render a single mermaid diagram via mermaid.ink and return image bytes.

    `width` + `scale` control output resolution (sharper text); `bg_color`
    forces an opaque background instead of the default transparent one.
    """
    encoded = mermaid_to_pako(diagram)
    params = {"bgColor": bg_color}
    if image_type == "svg":
        url = f"https://mermaid.ink/svg/{encoded}"
    else:
        url = f"https://mermaid.ink/img/{encoded}"
        params["type"] = image_type
        params["width"] = width
        params["scale"] = scale

    last_exc = None
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise last_exc


def process_file(
    md_path: Path, output_dir: Path, image_type: str, width: int, scale: float
) -> int:
    """Extract and render diagrams from one markdown file. Returns count rendered."""
    text = md_path.read_text(encoding="utf-8")
    diagrams = extract_diagrams(text)
    if not diagrams:
        print(f"  [skip] no mermaid diagrams found in {md_path.name}")
        return 0

    count = 0
    for i, diagram in enumerate(diagrams, start=1):
        suffix = "" if len(diagrams) == 1 else f"_{i}"
        out_name = f"{md_path.stem}{suffix}.{image_type}"
        out_path = output_dir / out_name
        try:
            image_bytes = render_diagram(
                diagram, image_type=image_type, width=width, scale=scale
            )
        except requests.RequestException as exc:
            print(f"  [error] failed to render diagram {i} in {md_path.name}: {exc}")
            continue
        out_path.write_bytes(image_bytes)
        print(f"  [ok] {md_path.name} -> {out_path}")
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Markdown file or directory to scan (default: current directory)",
    )
    parser.add_argument(
        "-o", "--output", default="output", help="Output directory (default: ./output)"
    )
    parser.add_argument(
        "-t",
        "--type",
        choices=("png", "svg"),
        default="png",
        help="Image type to generate (default: png)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1200,
        help="Output width in pixels for PNG/JPEG/WebP (default: 1200)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=3,
        help="Resolution scale factor 0-3 for sharper text (default: 3)",
    )
    args = parser.parse_args()

    input_path = Path(args.path)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if input_path.is_file():
        md_files = [input_path]
    elif input_path.is_dir():
        md_files = sorted(input_path.glob("*.md"))
    else:
        print(f"Error: path not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if not md_files:
        print(f"No markdown files found in {input_path}")
        sys.exit(0)

    total = 0
    for md_file in md_files:
        print(f"Processing {md_file}...")
        total += process_file(md_file, output_dir, args.type, args.width, args.scale)

    print(f"\nDone. Rendered {total} diagram(s) to {output_dir.resolve()}")


if __name__ == "__main__":
    main()
