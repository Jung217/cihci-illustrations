#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生 cihci-illustrations 的範例圖。

技能本身（技能本體）只負責想清楚要畫什麼、把提示詞寫對，生圖交給
代理內建的 image_gen。這支腳本是給「手邊沒有內建生圖工具、但有 OpenAI 金鑰」
的情況用的離線補救，用途只有一個：產出 assets/examples/ 底下的範例圖。

它照 references/prompt-template.md 組提示詞，並把
assets/ip/cihci.png 當參考圖一起送出——實測純文字描述會讓 CIHCI 醬在「明確
交叉的 X」和「寬扁緞帶比例」之間來回走鐘，餵參考圖才穩得住。

用法：

    export OPENAI_API_KEY=...
    python tools/generate_examples.py              # 全部
    python tools/generate_examples.py --only 01 03 # 只跑指定編號
    python tools/generate_examples.py --list       # 只列出 shot list，不生圖
    python tools/generate_examples.py --quality high

每張圖生完都要照 references/qa-checklist.md 人工檢查，不合格就重跑那一張。
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REF_IMAGE = REPO / "assets" / "ip" / "cihci.png"
OUT_DIR = REPO / "assets" / "examples"
ENDPOINT = "https://api.openai.com/v1/images/edits"

# 比例 -> API size。gpt-image 只吃這三種，取最接近的。
SIZE_BY_RATIO = {
    "16:9": "1536x1024",
    "3:2": "1536x1024",
    "4:3": "1536x1024",
    "1:1": "1024x1024",
}


# --------------------------------------------------------------------------
# 提示詞區塊（對應 references/prompt-template.md）
# --------------------------------------------------------------------------

VISUAL_DNA = """Visual DNA:
Pure white background. Minimalist black hand-drawn line art. Slightly wobbly pen lines. Lots of empty white space. Sparse handwritten Traditional Chinese annotations in red / orange / dark blue. Clean absurd product-sketch feeling. No gradients, no shadows, no paper texture, no complex background, no commercial vector style, no PPT infographic look, no cute mascot poster, no children's illustration, no realistic UI.
All text in the image must be Traditional Chinese (Taiwan). Absolutely no Simplified Chinese characters."""

IP_BLOCK = """Recurring IP character required - "CIHCI 醬":
The reference image is the CIHCI Lab logo. CIHCI 醬 is a small absurd creature whose BODY IS EXACTLY THAT LOGO SHAPE - same proportions, same two crossing translucent ribbons, same green overlap patch, same three dark-blue rounded squares, same colors. Copy the logo's silhouette and proportions faithfully; do not slim it into thin sticks, do not round it into petals or a bowtie, do not turn it into a butterfly or pinwheel.
Redraw it as if hand-drawn: edges slightly wobbly, corners not perfectly aligned, NOT clean vector shapes. No gradients, no glow, no drop shadow.
OUTLINE: the ribbons are flat blocks of color, each enclosed by a hand-drawn black contour line. The outline must run the FULL way around every ribbon - never outline only part of the body, and never leave a stroke unfinished.
Two round white eyes sit close together near the MIDDLE of the body, close to where the ribbons cross. Each holds one small black dot pupil. The eyes are small - the pair together spans about one quarter of the body's width.
GAZE IS THE CHARACTER'S ONLY EXPRESSION. It has no mouth and no eyebrows, so push both pupils off-centre so it reads as consciously looking at something. In this image the gaze target is: {gaze}
Blank, deadpan, serious expression. No mouth, no eyebrows, no blush.

LIMBS - keep them tiny and sparse; this character's charm comes from how little is drawn:
- Arms are thin black lines leaving the mid-height side edge of the body in a gentle curve. NO drawn elbow joint.
- Hands are the barest sketch at the end of a line - three or four short strokes like a claw, or one small blob closed around what it holds. NOT a full palm, NOT outlined fingers. So small they read as a change in the line, not as a hand.
- Only the arm nearest an object reaches for it, and it must actually touch what it holds.
- Legs are short thin black lines with one outward knee bend. Feet are two small diagonal strokes - no soles, no shoes. Legs are LINES, never rectangles or closed boxes.

Do not enlarge CIHCI 醬 in order to render its hands or feet legibly - those should stay too small to read in detail.

CIHCI 醬 must PERFORM the core conceptual action, not decorate the scene. Serious, deadpan, slightly bizarre - not cute, not a mascot.
CIHCI 醬 is the ONLY colored object in the whole image. Everything else is black hand-drawn line art. Do NOT reproduce the reference image's white background as a separate panel, frame or sticker - integrate the creature into the scene."""

COLOR_USE = """Color use:
CIHCI 醬 uses its own four logo colors and is the only colored object. All other line art, objects, frames and structure are black. Orange for main flow / path / arrows. Red only for key warnings, problems or results. Dark blue (#015DA0) only for secondary notes, feedback or system state - never use bright cyan for annotations, it would clash with CIHCI 醬's body."""

MODE_CASUAL = "Do not make it a formal flowchart, system architecture diagram, course slide, or dense explainer"
MODE_ACADEMIC = (
    "A method architecture / pipeline layout is allowed here, but keep it to at most 5-7 nodes, "
    "keep every box and arrow hand-drawn and wobbly, and keep at least 35% white space. "
    "Still no gradients, no glow, no flat vector style, no realistic UI"
)

RATIO_PHRASE = {
    "16:9": "16:9 horizontal",
    "3:2": "3:2 horizontal",
    "4:3": "4:3 horizontal",
    "1:1": "1:1 square",
}


def build_prompt(shot: dict) -> str:
    return f"""Generate one standalone {RATIO_PHRASE[shot['ratio']]} Traditional-Chinese illustration.

{VISUAL_DNA}

{IP_BLOCK.replace('{gaze}', shot['gaze'])}

Theme:
{shot['theme']}

Structure type:
{shot['structure']}

Core idea:
{shot['idea']}

Composition:
{shot['composition']}

Suggested elements:
{shot['elements']}

Traditional Chinese handwritten labels:
{shot['labels']}

{COLOR_USE}

Constraints:
One image explains only one core structure. Keep the main subject around 40%-60% of the canvas. Preserve at least 35% blank white space. Use at most 5-8 short handwritten Traditional Chinese labels. Do not write a title in the top-left corner. Do not write the structure type on the image. Do not render the words "CIHCI LAB" anywhere in the illustration. {shot['mode']}. Invent a fresh visual metaphor for this specific topic. It should be clear but not instructional, interesting but not childish, strange but clean."""


# --------------------------------------------------------------------------
# Shot list：每張圖換物件、換動作，不重複隱喻
# --------------------------------------------------------------------------

SHOTS = [
    {
        "id": "01",
        "slug": "data-bottleneck",
        "ratio": "16:9",
        "mode": MODE_CASUAL,
        "metaphor": "手搖壓麵機被線團塞住",
        "theme": "卡住的不是方法，是資料",
        "structure": "概念隱喻",
        "idea": "大家以為瓶頸在模型，其實瓶頸在更前面那一段；越用力調模型，越看不見真正塞住的地方",
        "gaze": (
            "its own hand on the crank, which is DOWN and to its LEFT. Both pupils sit against the "
            "bottom-left of the white eyes. It is stubbornly staring at the crank and pointedly NOT "
            "looking up at the clogged funnel above."
        ),
        "composition": (
            "畫面左側一台怪異的手搖式壓麵機，上方漏斗口塞著一團打結的線團完全下不去。搖桿裝在機器右側、"
            "朝向 CIHCI 醬。CIHCI 醬站在機器右邊，身體前傾很使勁。牠靠近機器那一側的手臂向左伸出，手指確實"
            "扣住搖桿把手（手要碰到把手，不是握空氣）；另一隻手臂垂在身體外側。牠低頭盯著自己扣住搖桿的那隻手，"
            "沒有抬頭看上方塞住的漏斗。機器下方出口只滴出一小滴。橙色箭頭沿機器由上往下標出應該的流向，"
            "在塞住處中斷。紅色圈標在線團上。"
        ),
        "elements": "手搖壓麵機 / 打結的線團 / 漏斗口 / 出口的一小滴",
        "labels": "卡在這（紅）/ 一直轉（深藍）/ 只出這麼多（紅）/ 沒人看上面（深藍）",
    },
    {
        "id": "02",
        "slug": "label-noise",
        "ratio": "1:1",
        "mode": MODE_CASUAL,
        "metaphor": "郵筒分揀時貼錯標籤",
        "theme": "標註品質決定天花板",
        "structure": "角色狀態",
        "idea": "資料集裡少數幾筆貼錯的標籤，會一路傳到最後的評估數字上，而且很難被發現",
        "gaze": (
            "the single wrong label in its own left hand, held up close. Both pupils pushed up and to "
            "the right, staring hard at that one label. It has just noticed something is off."
        ),
        "composition": (
            "畫面中央一排三個怪異的舊郵筒，投遞口上方各貼一張手寫標籤。CIHCI 醬站在郵筒前，右手正要把一封信"
            "投進中間那個郵筒，左手舉起一張標籤湊近眼前端詳——那張標籤的字跟郵筒上的不一樣。牠盯著手上那張標籤看。"
            "地上已經有幾封投錯的信散落。紅色圈標在手上那張標籤。深藍細線從郵筒延伸到畫面邊緣，表示錯誤會往後傳。"
        ),
        "elements": "三個舊郵筒 / 手寫標籤 / 散落的信 / 舉高的那張標籤",
        "labels": "這張不對（紅）/ 一路傳下去（深藍）/ 剩下的照投（深藍）",
    },
    {
        "id": "03",
        "slug": "method-architecture",
        "ratio": "3:2",
        "mode": MODE_ACADEMIC,
        "metaphor": "四層抽屜櫃，其中一層被抽出來換零件",
        "theme": "方法架構：四個模組，只有一層真的動過",
        "structure": "方法架構",
        "idea": "整條管線沿用既有架構，真正的貢獻集中在中間那一層；把它換掉，效果就掉回基準線",
        "gaze": (
            "the module it is holding in its hands, at chest height. Both pupils angled down and "
            "slightly right, focused on the part it is swapping in."
        ),
        "composition": (
            "畫面中央一個手繪的四層抽屜櫃，每層是一個模組方框，由下往上排。第三層的抽屜被完全拉出來，"
            "CIHCI 醬站在櫃子右側，雙手捧著一個小零件正要放進那個拉開的抽屜，左手托著零件、右手扶著抽屜邊緣。"
            "橙色箭頭沿櫃子右邊由下往上串起四層，表示資料流向。紅色框只標在第三層。其餘三層維持素描狀態。"
            "節點總數不超過五個，留白要足。"
        ),
        "elements": "四層抽屜櫃 / 拉開的第三層 / 手上的小零件 / 沿邊的流向箭頭",
        "labels": "輸入（黑）/ 換這層（紅）/ 其餘沿用（深藍）/ 輸出（黑）",
    },
    {
        "id": "04",
        "slug": "ablation",
        "ratio": "4:3",
        "mode": MODE_ACADEMIC,
        "metaphor": "投幣式秤重機，一次拿掉一枚硬幣",
        "theme": "消融實驗：拿掉哪一項，掉最多",
        "structure": "實驗設計",
        "idea": "逐項移除元件並重測，掉幅最大的那一項才是真正在work的部分",
        "gaze": (
            "the pointer on the scale dial, up and to its left. Both pupils pushed to the upper-left "
            "of the white eyes, watching the needle drop."
        ),
        "composition": (
            "畫面右側一台怪異的立式秤重機，秤面是一個大圓錶盤，指針明顯偏低。秤盤上放著三枚圓片，"
            "CIHCI 醬站在秤旁，右手正把第四枚圓片從秤盤上拿走，左手垂在身側。牠抬眼盯著錶盤上的指針看。"
            "被拿走那枚圓片用紅色標示，指針下掉處也用紅色短箭頭標。其餘三枚維持黑色線稿。"
            "元素總數不超過五個，畫面留白至少四成。"
        ),
        "elements": "立式秤重機 / 大圓錶盤與指針 / 秤盤上的圓片 / 被拿走的那一枚",
        "labels": "拿掉這個（紅）/ 掉最多（紅）/ 其他照舊（深藍）",
    },
    {
        "id": "05",
        "slug": "baseline-compare",
        "ratio": "3:2",
        "mode": MODE_ACADEMIC,
        "metaphor": "兩扇並排的窗，中間一支閘刀",
        "theme": "本方法與基準線的差別只在一個開關",
        "structure": "結果對照",
        "idea": "兩邊條件完全相同，只有中間那個開關的位置不一樣，output的乾淨程度差很多",
        "gaze": (
            "the right-hand window, which shows the clean result. Both pupils pushed to the right edge "
            "of the white eyes, checking the outcome of the switch it just threw."
        ),
        "composition": (
            "畫面上左右並排兩扇一樣大的手繪方窗，左窗裡的線條雜亂糾結，右窗裡的線條乾淨整齊。"
            "兩窗中間下方有一支老式閘刀開關，CIHCI 醬站在開關旁，右手把閘刀往右推到底，左臂自然垂下。"
            "牠轉頭看向右邊那扇窗。橙色短箭頭從開關指向右窗。左窗用紅色標，右窗用深藍標。"
            "除了兩扇窗和一支閘刀，不要再加其他物件。"
        ),
        "elements": "兩扇並排方窗 / 老式閘刀開關 / 左窗的雜亂線條 / 右窗的乾淨線條",
        "labels": "基準線（紅）/ 同樣的資料（深藍）/ 本方法（深藍）",
    },
]


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def _multipart(fields: dict, files: list) -> tuple:
    boundary = uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'
        ).encode()
    for key, path in files:
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{key}"; filename="{Path(path).name}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode()
        body += Path(path).read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return bytes(body), boundary


def generate(shot: dict, out_path: Path, model: str, quality: str, ref: Path) -> None:
    fields = {
        "model": model,
        "prompt": build_prompt(shot),
        "size": SIZE_BY_RATIO[shot["ratio"]],
        "quality": quality,
        "n": "1",
    }
    body, boundary = _multipart(fields, [("image[]", ref)])
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
        print(f"  HTTP {exc.code}: {exc.read().decode()[:400]}", file=sys.stderr)
        raise

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(payload["data"][0]["b64_json"]))
    usage = payload.get("usage", {})
    kb = out_path.stat().st_size // 1024
    print(f"  OK  {out_path.relative_to(REPO)}  {kb} KB  tokens={usage.get('total_tokens')}")


def main() -> int:
    ap = argparse.ArgumentParser(description="產生 cihci-illustrations 範例圖")
    ap.add_argument("--only", nargs="+", metavar="ID", help="只跑指定編號，例如 --only 01 03")
    ap.add_argument("--list", action="store_true", help="只列出 shot list，不呼叫 API")
    ap.add_argument("--model", default="gpt-image-2")
    ap.add_argument("--quality", default="medium", choices=["low", "medium", "high"])
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--ref", type=Path, default=REF_IMAGE)
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    shots = SHOTS
    if args.only:
        wanted = set(args.only)
        shots = [s for s in SHOTS if s["id"] in wanted]
        missing = wanted - {s["id"] for s in SHOTS}
        if missing:
            print(f"找不到編號：{', '.join(sorted(missing))}", file=sys.stderr)
            return 2

    if args.list:
        for s in shots:
            print(f"{s['id']}  {s['ratio']:<5} {s['slug']}")
            print(f"      主題：{s['theme']}")
            print(f"      結構型：{s['structure']}    隱喻：{s['metaphor']}")
        return 0

    if not os.environ.get("OPENAI_API_KEY"):
        print("缺少 OPENAI_API_KEY 環境變數。", file=sys.stderr)
        return 2
    if not args.ref.exists():
        print(f"找不到參考圖：{args.ref}", file=sys.stderr)
        return 2

    failures = []
    for s in shots:
        print(f"[{s['id']}] {s['slug']}  ({s['ratio']}, {s['structure']})")
        out = args.out / f"{s['id']}-{s['slug']}.png"
        try:
            generate(s, out, args.model, args.quality, args.ref)
        except Exception as exc:  # noqa: BLE001 - 單張失敗不該中斷整批
            print(f"  失敗：{exc}", file=sys.stderr)
            failures.append(s["id"])

    print()
    print(f"完成 {len(shots) - len(failures)}/{len(shots)} 張。")
    if failures:
        print(f"失敗：{', '.join(failures)}")
    print("請照 references/qa-checklist.md 逐張檢查，不合格就重跑該編號。")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
