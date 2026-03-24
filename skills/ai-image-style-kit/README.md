# 🎨 ai-image-style-kit

火山引擎豆包图像风格提取与生成工具。支持从参考图提取画风风格、保存到风格库、用文字描述+风格生成图片。

---

## 功能

| 功能 | 说明 |
|------|------|
| **提取风格** | 上传参考图，AI 分析画风风格并保存 |
| **生成图片** | 输入文字描述 + 指定风格，生成同风格图片 |
| **风格管理** | 支持命名风格、模糊匹配、查看列表 |

---

## 快速开始

### 环境配置

```bash
export ARK_API_KEY="你的火山引擎 ARK API Key"
```

获取方式：[火山引擎控制台](https://www.volcengine.com/docs/82379/1399008)

### 提取风格

```bash
python3 scripts/doubao_image_ops.py analyze <图片路径或URL> [--name=风格名称]
```

示例：
```bash
# 提取风格并命名为"科技感"
python3 scripts/doubao_image_ops.py analyze ./demo.jpg --name=科技感
```

### 生成图片

```bash
# 使用风格生成（推荐）
python3 scripts/doubao_image_ops.py use <风格编号或名称> "<生图描述>" [--size=16:9]

# 纯文字生成（不使用风格）
python3 scripts/doubao_image_ops.py generate "<生图描述>" [--size=16:9]
```

示例：
```bash
# 用名称引用风格
python3 scripts/doubao_image_ops.py use "科技感" "AI时代配图" --size=16:9

# 用编号引用风格
python3 scripts/doubao_image_ops.py use 1 "AI时代配图" --size=16:9
```

### 查看风格列表

```bash
python3 scripts/doubao_image_ops.py list
```

---

## 尺寸参数

支持多种格式：
- 比例：`16:9`、`4:3`、`1:1`（默认 `16:9`）
- 像素：`1920x1080`、`1024x1024`

---

## 风格库

风格文件保存在 `scripts/styles/style_XXX.json`，包含：

| 字段 | 说明 |
|------|------|
| `id` | 风格编号 |
| `style_name` | 风格名称（可选） |
| `style_description` | 风格描述 |
| `source_image` | 来源图片 |
| `saved_at` | 保存时间 |

---

## 飞书发送（可选）

需要配置飞书应用凭证：

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
```

然后使用脚本发送图片到飞书：
```bash
python3 scripts/feishu_send_image.py <图片URL或本地路径>
```

---

## 依赖

```
pip install requests
```

---

## 项目结构

```
ai-image-style-kit/
├── SKILL.md                         # OpenClaw Skill 定义
├── scripts/
│   ├── doubao_image_ops.py          # 主脚本（analyze/use/generate/list）
│   ├── feishu_send_image.py         # 飞书发图脚本
│   └── styles/                      # 风格存储目录
│       ├── style_001.json
│       └── style_002.json
└── README.md
```

---

_Built with 火山引擎豆包 + OpenClaw_
