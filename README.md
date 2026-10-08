# 公众号双版本封面 skill

一套面向公众号和长文的封面工作流：**先读文章，再制作实景摄影版和 AI 主题背景版两张完成排版的封面。**

![实景摄影封面示例](references/approved-cover.jpg)

摄影版保留真实照片的空间、光线和质感；AI 版根据文章主旨独立生成背景，再准确排入标题。选图与构图随文章调整，不固定套用同一张模板。

## 它会做什么

1. 阅读正文，提炼主旨和适合封面的文案。
2. 检查文章配图；不合适时到文章之外寻找有出处、有许可的真实摄影，完成实景版。
3. 根据主旨用内置 image_gen 生成另一张无字背景，完成 AI 版。
4. 检查两张原尺寸成品和手机缩略图。
5. 交付两张有字效果图、各自无字版，以及摄影来源和生成说明；用户明确只要一个方向时按具体要求处理。

默认横版尺寸为 **2350 × 1000（2.35:1）**。这只是工作流默认值，可以修改。

## 安装到 Codex

将这个仓库克隆到个人技能目录，并保留技能文件夹名 `wechat-photo-cover`：

```bash
git clone https://github.com/ZSeekin/wechat-photo-cover-skill.git "${CODEX_HOME:-$HOME/.codex}/skills/wechat-photo-cover"
```

如果同名技能目录已经存在，请保留现有文件，选择合适的更新方式；上面的命令用于首次安装。

在任务中附上文章内容或链接，然后说：

> 请用 $wechat-photo-cover 给这篇文章做实景摄影版和 AI 背景版两张封面，保留各自无字版和素材说明。

也可以直接指定照片、标题或比例：

> 用 $wechat-photo-cover，把我给的照片做成 16:9 的无字封面。

## 本地排版脚本

脚本只处理本地图片，包括已下载的照片和已生成的背景；它不联网、不调用生图模型。运行需要 Python 3.9+、Pillow 和可用的中文字体。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/render_cover.py --config references/example-cover.json --output-dir outputs/example
```

以上命令可使用仓库自带的参考照片生成示例。实际任务需分别为摄影版和 AI 版准备本地背景图与配置文件，保持标题、尺寸相同，并设置不同的 `stem`；配置中的字段仍叫 `photo`：

```json
{
  "photo": "my-photo.jpg",
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

`photo` 可指向摄影或 AI 背景；相对路径从配置文件所在目录解析。标题和其他文字均可省略。macOS 默认寻找冬青黑体中文；其他系统可使用 Noto Sans CJK / Source Han Sans，或通过 `font_path` 指定字体。

每个配置各输出有字与无字两组 JPG、PNG，以及宽 470 像素的缩略图。源图不覆盖。脚本会检查非法裁切、文字越界、重叠和缺字等问题，但最终仍需要看图验收。

完整配置说明见 [渲染用法](references/rendering.md)。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| [SKILL.md](SKILL.md) | 选图、设计、检查和交付工作流 |
| [agents/openai.yaml](agents/openai.yaml) | 技能名称、简介和默认调用提示 |
| [scripts/render_cover.py](scripts/render_cover.py) | 确定性的本地图片裁切排版 |
| [references/style-and-example.md](references/style-and-example.md) | 已认可的风格、构图分析和素材出处 |
| [references/rendering.md](references/rendering.md) | 脚本配置说明 |
| [references/example-cover.json](references/example-cover.json) | 可直接运行的示例配置 |

## 示例摄影来源

示例照片由 [Michael Gluzman](https://unsplash.com/photos/aerial-view-of-a-foggy-city-with-a-river-aD0nD0sqUaM) 拍摄，适用 [Unsplash License](https://unsplash.com/license)。仓库内示例经过裁切、轻微亮度调整和文字排版，没有使用 AI 生成或扩展画面。

照片用于表现主题和氛围，不是文章案例的现场图。原作链接和处理记录见 [素材说明](references/style-and-example.md)。
