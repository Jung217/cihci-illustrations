#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生 CIHCI 醬的角色設定圖。

內容依 references/cihci-ip.md 而來：主站姿、三個識別要件、
視線方向變化、手腳畫法，以及幾個常犯的錯誤示範。

輸出到 assets/ip/cihci-chan-model-sheet.png，可以跟 cihci.png
一起當參考圖餵給圖像模型。

用法：

    export OPENAI_API_KEY=...
    python tools/generate_model_sheet.py
    python tools/generate_model_sheet.py --quality high
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_examples import ENDPOINT, REF_IMAGE, REPO, _multipart  # noqa: E402

OUT = REPO / "assets" / "ip" / "cihci-chan-model-sheet.png"

PROMPT = """Generate one 3:2 horizontal character model sheet on a pure white background.

This is a reference sheet for an illustration style guide, drawn as if sketched by hand on white paper. Minimalist black hand-drawn line art, slightly wobbly pen lines, generous white space between the panels. No gradients, no shadows, no paper texture, no vector polish, no PPT look, no frames or borders around the sheet.
All text must be handwritten Traditional Chinese (Taiwan). Absolutely no Simplified Chinese characters. Keep every label to 2-7 characters.

THE CHARACTER - "CIHCI 醬". The reference image is the CIHCI Lab logo; the character's body IS that logo shape.

BODY:
- Two translucent ribbons overlap into an X / butterfly silhouette: a sky-blue (#2EB1FF) ribbon running from upper-left down to lower-right, a hot-pink (#FF63B2) ribbon running from upper-right down to lower-left.
- Where the two ribbons overlap, green (#36B729) shows through; that patch sits toward the lower right.
- Three small dark-blue (#015DA0) rounded squares sit at the ENDS of the ribbons and at the CROSSING point, like joints or fasteners.
- The ribbon edges are hand-drawn: visibly wobbly, corners not quite meeting, clearly not precise vector shapes.
- Fill: each ribbon is ONE flat, SOLID, perfectly uniform block of color - the exact same hue from edge to edge. No texture, no crayon or coloured-pencil shading, no visible strokes inside the shape, no hatching, no gradient, no paper grain, no lighter or darker patches. The only place the colour changes is the green overlap.
- Outline: the ribbons are solid blocks of color with a black contour line along the edge. The outline runs the complete way around - never only partway.
- The overall silhouette must read at a glance as that X. Do not draw a tidy bow-tie or a pinwheel.

HUMAN-LIKE FEATURES:
- Eyes: two white dots side by side, each holding one small black dot pupil, sitting at the middle of the body near the ribbon crossing. They are SMALL - the pair spans about a quarter of the body's width.
- Gaze: it has no mouth and no eyebrows, so pupil direction is its only expression. Pupils sit off-centre, aimed at whatever it is looking at.
- Arms: thin black lines leaving the mid-height side edges of the body in a natural curve. No elbow joint. Draw both arms.
- Hands: the barest sketch at the end of a line - three or four short strokes like a claw, or a small blob closed around something. Never a full palm; small enough to read as a change in the line.
- Legs: short and thin, one outward bend at the knee, feet are just two small diagonal strokes with no soles. The stance forms a stable triangle.
- Expression blank, dull, calm, serious. No mouth, no eyebrows, no blush.

CHARACTER: earnest but doing something absurd; a low-key system operator; dry humour, never coy; a bit clumsy but not stupid.

NEVER: an over-cute mascot; a children's cartoon; elaborate clothing; shiny sparkling eyes; too commercial, too rounded, too polished; a full palm, a drawn elbow, or soled feet; gradients, glow or drop shadow on the ribbons; textured, crayon-like or pencil-shaded fills; the words "CIHCI LAB".

The character is the ONLY colored thing on the sheet. Every label, arrow and wrong-example is plain black line art, except the small red crosses noted below.

LAYOUT - four zones, clearly separated by white space, no boxes drawn around them:

1) LEFT, largest: one big front-facing standing pose of CIHCI 醬, both arms visible and relaxed at its sides, pupils looking slightly left. Three short thin black arrows point from this figure to three short handwritten labels placed in the white space around it:
   - an arrow to the ribbon crossing, labelled 兩帶交疊成 X
   - an arrow to the green overlap patch, labelled 重疊處是綠
   - an arrow to one of the dark-blue squares, labelled 三顆深藍方塊

2) TOP RIGHT: a horizontal row of four small copies of the character's eye area only - the two white dot eyes with their black pupils, drawn on a small piece of the sky-blue ribbon. The four differ only in pupil direction: pressed left, pressed right, pressed up, pressed down. No two may look alike. One short label under the row: 視線＝唯一表情

3) MIDDLE RIGHT: two small detail sketches, drawn larger than life like a zoomed-in note:
   - a hand: a thin line ending in three short strokes, labelled 手是線的末端
   - a leg: a short thin line with one outward knee bend and two small diagonal strokes for the foot, labelled 腿有膝彎

4) BOTTOM RIGHT: a row of three small WRONG examples of the character, each drawn smaller and simpler, each marked with a small red cross above it and a short black label under it:
   - a version whose outline is drawn on only half the body, labelled 描一半
   - a version with big rounded cartoon hands with fingers, labelled 完整手掌
   - a version drawn as a cute mascot with big shiny eyes and a smile, labelled 太可愛

Do not write a title anywhere on the sheet. Do not render the words "CIHCI LAB" or any English text. Do not number the zones. Keep at least a third of the sheet as empty white paper."""


def main() -> int:
    ap = argparse.ArgumentParser(description="產生 CIHCI 醬角色設定圖")
    ap.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    ap.add_argument("--model", default="gpt-image-2")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not os.environ.get("OPENAI_API_KEY"):
        print("缺少 OPENAI_API_KEY 環境變數。", file=sys.stderr)
        return 2

    fields = {
        "model": args.model,
        "prompt": PROMPT,
        "size": "1536x1024",
        "quality": args.quality,
        "n": "1",
    }
    body, boundary = _multipart(fields, [("image[]", REF_IMAGE)])
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()[:400]}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(base64.b64decode(payload["data"][0]["b64_json"]))
    try:
        shown = args.out.relative_to(REPO)
    except ValueError:
        shown = args.out
    print(f"OK  {shown}  {args.out.stat().st_size // 1024} KB")
    print("請對照 references/cihci-ip.md 檢查三要件、描邊完整度與中文字。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
