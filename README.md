# mermaid2image

A small Python CLI tool that scans Markdown (`.md`) files for [Mermaid](https://mermaid.js.org/)
diagrams and renders each one to an image (PNG or SVG) using the free
[mermaid.ink](https://mermaid.ink) rendering service — no local Chromium/Puppeteer
install required.

## Features

- Scans a single Markdown file or an entire folder of `.md` files.
- Extracts diagrams from:
  - fenced ` ```mermaid ... ``` ` code blocks, **and**
  - files that contain a raw diagram with no fences (e.g. a file that just
    starts with `flowchart`, `sequenceDiagram`, `classDiagram`, etc.).
- Supports multiple diagrams per file (numbered output files).
- Renders with an opaque **white background** (instead of mermaid.ink's
  default transparent background).
- Renders at a configurable **width/scale** for crisp, high-resolution text.
- Retries automatically on transient network errors.

## Requirements

- Python 3.10+
- [`requests`](https://pypi.org/project/requests/)
- An internet connection (diagrams are rendered via the mermaid.ink API)

Install the dependency:

```powershell
pip install requests
```

## Usage

```powershell
python mermaid2image.py [path] [-o OUTPUT_DIR] [-t {png,svg}] [--width WIDTH] [--scale SCALE]
```

| Argument         | Description                                                                 | Default     |
|------------------|-------------------------------------------------------------------------------|-------------|
| `path`           | A markdown file or a directory containing markdown files.                   | `.` (cwd)   |
| `-o`, `--output` | Directory to write rendered images to.                                      | `./output`  |
| `-t`, `--type`   | Image type to generate: `png` or `svg`.                                     | `png`       |
| `--width`        | Output width in pixels (PNG/JPEG/WebP only).                                 | `1200`      |
| `--scale`        | Resolution scale factor, `0`–`3` (higher = sharper text, requires `--width`).| `3`         |

### Examples

Render every `.md` file in the current folder to `./output`:

```powershell
python mermaid2image.py .
```

Render a single file to a custom folder:

```powershell
python mermaid2image.py mermaid3.md -o images
```

Generate SVG instead of PNG:

```powershell
python mermaid2image.py . -t svg
```

Produce larger, extra-sharp PNGs for a dense diagram:

```powershell
python mermaid2image.py mermaid2.md --width 2000 --scale 3
```

## Output

For each diagram found, an image is saved as `<filename>.<ext>` (or
`<filename>_<n>.<ext>` if a file contains more than one diagram), e.g.:

```
output/
├── mermaid.png
├── mermaid2.png
└── mermaid3.png
```

## How it works

1. Each file is read and scanned for fenced ` ```mermaid ` blocks; if none
   are found, the whole file is treated as one diagram if it starts with a
   recognized Mermaid diagram keyword.
2. Each diagram's source is JSON-wrapped, zlib-compressed, and base64url
   encoded (the same "pako" format used by the Mermaid Live Editor).
3. The encoded diagram is sent to `https://mermaid.ink/img/...` (or `/svg/...`)
   with `bgColor`, `width`, and `scale` query parameters, and the returned
   image bytes are saved to disk.

## Notes / Limitations

- Requires network access to `mermaid.ink`; there is no fully offline mode.
- `mermaid.ink` is a third-party free service — very large or complex
  diagrams may occasionally time out (the tool retries up to 3 times).
