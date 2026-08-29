# 生圖提示詞範本

每張圖單獨生成。依內容替換變數，不要把多張圖拼在一起。

## IP 描述區塊（每張圖都要原樣帶上）

這段是 CIHCI 醬的外形定義，不要改寫、不要縮寫、不要只寫「CIHCI 醬」四個字就當作交代過了。圖像模型不認得這個角色，每次都得完整描述。

```text
Recurring IP character required — "CIHCI 醬":
A small absurd creature whose body IS the CIHCI Lab logo: two overlapping translucent ribbon-like polygons crossing in an X / butterfly silhouette. One sky-blue ribbon (#2EB1FF) runs from upper-left down to lower-right; one hot-pink ribbon (#FF63B2) runs from upper-right down to lower-left. Where the two ribbons overlap, toward the lower right, the color reads green (#36B729). Three small dark-blue (#015DA0) rounded squares sit at the ribbon ends and at the crossing point, like joints or fasteners.
The ribbon edges are hand-drawn: slightly wobbly, corners not perfectly aligned, NOT clean vector shapes. No gradients, no glow, no drop shadow on the ribbons.
Two white dot eyes sit on the upper-left sky-blue ribbon. Thin black hand-drawn legs, occasionally thin arms. Blank, deadpan, serious expression. No mouth, no eyebrows, no blush.
CIHCI 醬 must PERFORM the core conceptual action, not decorate the scene. Serious, deadpan, slightly bizarre — not cute, not a mascot.
CIHCI 醬 is the ONLY colored object in the whole image. Everything else is black hand-drawn line art.
```

若生圖工具支援參考圖，把 `assets/ip/cihci.png` 一起餵進去，辨識度會穩很多——尤其是三個深藍方塊和綠色重疊區，純文字描述常常掉。

不要餵含字版 `assets/ip/cihcilab.png`，否則圖裡會冒出「CIHCI LAB」字樣。

## 主範本

```text
Generate one standalone {比例} Traditional-Chinese illustration.

Visual DNA:
Pure white background. Minimalist black hand-drawn line art. Slightly wobbly pen lines. Lots of empty white space. Sparse handwritten Traditional Chinese annotations in red / orange / dark blue. Clean absurd product-sketch feeling. No gradients, no shadows, no paper texture, no complex background, no commercial vector style, no PPT infographic look, no cute mascot poster, no children's illustration, no realistic UI.
All text in the image must be Traditional Chinese (Taiwan). Absolutely no Simplified Chinese characters.

{貼上上面整段 IP 描述區塊}

Theme:
{配圖主題}

Structure type:
{結構型：Workflow / 系統局部 / 前後對比 / 角色狀態 / 概念隱喻 / 方法分層 / 地圖路線 / 小漫畫分鏡 / 方法架構 / 實驗設計 / 資料流 / 結果對照}

Core idea:
{這張圖要表達的核心意思}

Composition:
{具體畫面：CIHCI 醬在哪裡、正在做什麼、主要物件是什麼、資訊如何流動}

Suggested elements:
{元素1} / {元素2} / {元素3} / {元素4}

Traditional Chinese handwritten labels:
{批註詞1} / {批註詞2} / {批註詞3} / {批註詞4} / {可選批註詞5}

Color use:
CIHCI 醬 uses its own four logo colors and is the only colored object. All other line art, objects, frames and structure are black. Orange for main flow / path / arrows. Red only for key warnings, problems or results. Dark blue (#015DA0) only for secondary notes, feedback or system state — never use bright cyan for annotations, it would clash with CIHCI 醬's body.

Constraints:
One image explains only one core structure. Keep the main subject around 40%-60% of the canvas. Preserve at least 35% blank white space. Use at most 5-8 short handwritten Traditional Chinese labels. Do not write a title in the top-left corner. Do not write the structure type on the image. Do not render the words "CIHCI LAB" anywhere in the illustration. {模式約束}. Invent a fresh visual metaphor for this specific topic; do not reuse a metaphor already used in this batch. It should be clear but not instructional, interesting but not childish, strange but clean.
```

### `{比例}` 對照

| 用途 | 填入 |
| :--- | :--- |
| 文章正文配圖、投影片 | `16:9 horizontal` |
| 社群貼文 | `1:1 square` |
| 論文圖（單欄） | `3:2 horizontal` |
| 論文圖（雙欄跨欄） | `4:3 horizontal` 或 `1:1 square` |

### `{模式約束}` 對照

怪誕正文模式（預設）填：

```text
Do not make it a formal flowchart, system architecture diagram, course slide, or dense explainer
```

學術圖解模式填：

```text
A method architecture / pipeline layout is allowed here, but keep it to at most 5-7 nodes, keep every box and arrow hand-drawn and wobbly, and keep at least 35% white space. Still no gradients, no glow, no flat vector style, no realistic UI
```

## 圖像編輯提示

去掉左上角標題：

```text
Edit the provided image. Remove only the handwritten title "{要刪除的文字}" and its underline from the top-left corner. Fill that area with the same clean white background, matching the surrounding blank paper. Preserve everything else exactly: characters, labels, paths, line style, composition, aspect ratio, and image quality. Do not add any new text or objects.
```

修 CIHCI 醬走形：

```text
Edit the provided image. Keep the composition, labels, and all black line art exactly as they are. Only redraw the CIHCI 醬 character so that it clearly reads as the logo: two overlapping hand-drawn translucent ribbons crossing in an X — sky-blue (#2EB1FF) from upper-left to lower-right, hot-pink (#FF63B2) from upper-right to lower-left, a green (#36B729) region where they overlap toward the lower right, and three small dark-blue (#015DA0) rounded squares at the ribbon ends and crossing point. Keep its two white dot eyes, thin black legs, and blank deadpan expression. Do not add color to anything else in the image.
```

增強荒誕感：

```text
Regenerate this illustration with the same core meaning and simple layout, but make CIHCI 醬 more central to the conceptual action. It should be doing the strange work that explains the idea, not standing beside the diagram. Keep it clean, sparse, hand-drawn, and not cute.
```

修簡體字：

```text
Edit the provided image. Some handwritten Chinese labels use Simplified characters. Rewrite every Chinese label in Traditional Chinese (Taiwan), keeping the same words, the same handwritten style, the same positions and the same colors. Change nothing else.
```
