# 确定性摄影封面渲染

`scripts/render_cover.py` 只处理已有的本地照片；选图、文章理解、许可核对和视觉验收由技能工作流完成。需要 Python 3 和 Pillow。

## 运行

在技能目录下运行：

```bash
python3 scripts/render_cover.py --config references/example-cover.json --output-dir /absolute/path/to/work/cover-preview
```

换成新文章时，复制示例 JSON 到当前任务工作目录，替换 `photo` 和文案，再将输出目录设为当前任务授权的成品目录。`photo` 相对路径从 JSON 所在目录解析。不要把脚本输出目录设成原照片文件。

## 配置

```json
{
  "photo": "local-photo.jpg",
  "stem": "article-cover",
  "size": [2350, 1000],
  "focus": [0.5, 0.5],
  "brightness": 1.0,
  "overlay_opacity": 0.3,
  "kicker": "文章主题",
  "title": ["第一行短标题", "第二行短标题"],
  "subtitle": "一行可选的具体说明"
}
```

- `photo`：必填，本地图片。
- `stem`：输出文件名，不含扩展名。
- `size`：成品像素尺寸，默认 `[2350, 1000]`。
- `focus`：等比填充裁切时的水平、垂直位置，范围 0–1。`[0,0]` 靠左上，`[1,1]` 靠右下。
- `crop_box`：可选原图像素范围 `[left, top, right, bottom]`，坐标基于应用 EXIF 朝向后的图片；指定后先裁切此区域，再居中等比填充目标比例。
- `brightness`：亮度乘数，默认不调整。慎用大幅调色。
- `overlay_opacity`：仅有字版左侧渐变的强度，范围 0–0.6。无字版不加排字遮罩。
- `kicker`、`title`、`subtitle`：均可省略；`title` 是一至两行字符串数组。
- `font_path`：可选中文字体文件；TTC 字重可用 `font_index` 指定整数或 `{"title":2,"body":0}`。
- `colors`：支持 `kicker`、`title`、`subtitle`、`accent`、`overlay` 五个颜色键，值为十六进制颜色或 Pillow 支持的色名。
- `layout`：主要支持 `kicker_xy`、`title_xy`、`title_line_gap`、`subtitle_xy`、`kicker_font_size`、`title_font_size`、`subtitle_font_size`、`text_width`。设置 `accent_line: null` 可关闭短装饰线。坐标和字号使用 2350 × 1000 的设计坐标，脚本随成品尺寸缩放；完整默认值见脚本开头的 `LAYOUT`。

macOS 默认寻找冬青黑体中文字体，标题 W6、其他文字 W3。其他系统优先可用的 Noto CJK / Source Han；找不到中文字体时显式指定，不用缺字字体勉强导出。

## 输出与限制

输出包括 `-clean.jpg/png`（无字版）、`-cover.jpg/png`（有字版）和对应 `-mobile.jpg` 缩略图。脚本会检查裁切范围与文字溢出，源照片不覆盖。过长文案应先缩短，再考虑字号与布局。

默认版式适合左文右景；不代替设计判断。不能为了适配默认坐标而遮挡主景或把照片裁坏。读取输出图和手机缩略图后，再决定是否交付。
