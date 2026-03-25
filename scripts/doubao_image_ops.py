#!/usr/bin/env python3
"""
火山引擎豆包图像分析与生成工具
- 风格分析：doubao-seed-2-0-pro-260215
- 图像生成：doubao-seedream-5-0-260128

存储机制：
  scripts/styles/style_XXX.json  — 每风格一个文件
"""

import sys
import json
import os
import time
import base64
from typing import Optional

try:
    import requests
except ImportError:
    print("需要安装 requests: pip install requests")
    sys.exit(1)

# 默认 API 配置
DEFAULT_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_IMAGE_MODEL = "doubao-seedream-5-0-260128"
DEFAULT_ANALYZE_MODEL = "doubao-seed-2-0-pro-260215"
STYLES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")


# ─────────────────────────────────────────────
# 存储机制
# ─────────────────────────────────────────────

def get_styles_dir() -> str:
    os.makedirs(STYLES_DIR, exist_ok=True)
    return STYLES_DIR


def _next_style_id() -> int:
    """返回下一个可用的风格编号"""
    existing = []
    for f in os.listdir(get_styles_dir()):
        if f.startswith("style_") and f.endswith(".json"):
            try:
                existing.append(int(f.split("_")[1].split(".")[0]))
            except ValueError:
                pass
    return (max(existing) + 1) if existing else 1


def save_style(style_description: str, source_image: str = "", style_name: str = "") -> dict:
    """保存风格到 JSON 文件，返回 {success, style_id, path}"""
    style_id = _next_style_id()
    record = {
        "id": style_id,
        "style_name": style_name,
        "style_description": style_description,
        "source_image": source_image,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    path = os.path.join(get_styles_dir(), f"style_{style_id:03d}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return {"success": True, "style_id": style_id, "path": path}


def load_style(style_id_or_name: str) -> dict:
    """
    加载风格记录。
    参数可以是：
    - 风格编号（如 "3"）
    - 风格名称（支持模糊匹配，如 "信息图"）
    - 文件名（如 "style_003.json"）
    - 完整路径
    """
    styles_dir = get_styles_dir()
    target = style_id_or_name.strip()

    # 尝试作为编号查找
    try:
        sid = int(target)
        path = os.path.join(styles_dir, f"style_{sid:03d}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return {"success": True, "record": json.load(f)}
    except ValueError:
        pass

    # 尝试作为风格名称模糊匹配
    for f in sorted(os.listdir(styles_dir)):
        if not (f.startswith("style_") and f.endswith(".json")):
            continue
        with open(os.path.join(styles_dir, f), encoding="utf-8") as fp:
            record = json.load(fp)
            name = record.get("style_name", "")
            if name and target.lower() in name.lower():
                return {"success": True, "record": record}

    # 尝试作为文件名
    if not os.path.isabs(style_id_or_file):
        style_id_or_file = os.path.join(styles_dir, style_id_or_file)

    if os.path.exists(style_id_or_file):
        with open(style_id_or_file, encoding="utf-8") as f:
            return {"success": True, "record": json.load(f)}

    return {"success": False, "error": f"未找到风格: {style_id_or_file}"}


def list_styles() -> list:
    """返回所有已保存风格的列表，按编号排序"""
    records = []
    for f in sorted(os.listdir(get_styles_dir())):
        if f.startswith("style_") and f.endswith(".json"):
            with open(os.path.join(get_styles_dir(), f), encoding="utf-8") as fp:
                try:
                    records.append(json.load(fp))
                except Exception:
                    pass
    return records


def fuse_prompt(user_prompt: str, style_description: str) -> str:
    """
    将用户描述与风格描述融合为最终生图 prompt。
    """
    return (
        f"{user_prompt}，"
        f"风格要求：{style_description.strip()}"
    )


# ─────────────────────────────────────────────
# API 调用
# ─────────────────────────────────────────────

def get_ark_api_key() -> str:
    api_key = os.environ.get("ARK_API_KEY", "")
    if not api_key:
        raise ValueError("未配置 ARK_API_KEY 环境变量，请先设置：export ARK_API_KEY=你的APIKey")
    return api_key


def analyze_style(image_path_or_url: str, prompt: Optional[str] = None) -> dict:
    api_key = get_ark_api_key()

    if prompt is None:
        prompt = """提取一下这张图片的风格，反推出通用的提示词，全程忽略图片所有人物、物体、场景、文字，零具象内容描述，不复刻画面、不推荐元素、深度拆解可跨主体复用的画风风格规则，量化精准输出，最终只输出一个生成提示词的提示词，不需要给任何案例"""

    # 构建 image content
    if image_path_or_url.startswith(("http://", "https://")):
        image_content = {"type": "input_image", "image_url": image_path_or_url}
    else:
        with open(image_path_or_url, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")
        ext = image_path_or_url.lower().split(".")[-1]
        mime_type = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "gif": "image/gif", "webp": "image/webp"
        }.get(ext, "image/jpeg")
        image_content = {"type": "input_image", "image_url": f"data:{mime_type};base64,{img_data}"}

    payload = {
        "model": DEFAULT_ANALYZE_MODEL,
        "input": [{"role": "user", "content": [image_content, {"type": "input_text", "text": prompt}]}]
    }

    try:
        resp = requests.post(
            f"{DEFAULT_API_BASE}/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload, timeout=60
        )
        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:500]}"}

        data = resp.json()
        if "error" in data:
            return {"success": False, "error": data["error"]}

        output_text = ""
        if "output" in data:
            for item in data["output"]:
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            output_text = c.get("text", "")

        return {"success": True, "style_description": output_text}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时"}
    except Exception as e:
        return {"success": False, "error": f"分析失败: {str(e)}"}


def generate_image(prompt: str, size: str = "16:9", watermark: bool = False) -> dict:
    api_key = get_ark_api_key()
    # 标准化 size：
    # - 16:9 / 4:3 等比例 -> 透传
    # - WIDTHxHEIGHT 像素 -> 透传
    # - 1k/2k/3k/4k -> 小写规范化
    normalized = size.strip()
    lower = normalized.lower()
    if lower in ("1k", "2k", "3k", "4k"):
        normalized = lower
    elif "x" not in normalized and ":" not in normalized:
        # 纯数字结尾如 "2K" -> 小写
        normalized = lower.rstrip("k") + "k"

    payload = {
        "model": DEFAULT_IMAGE_MODEL,
        "prompt": prompt,
        "sequential_image_generation": "disabled",
        "response_format": "url",
        "size": normalized,
        "stream": False,
        "watermark": watermark
    }

    try:
        resp = requests.post(
            f"{DEFAULT_API_BASE}/images/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload, timeout=60
        )
        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:500]}"}

        data = resp.json()
        if "error" in data:
            return {"success": False, "error": data["error"]}

        # 有些 API 直接返回图片 URL（data 是数组）
        if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
            first = data["data"][0]
            if "url" in first:
                return {"success": True, "image_url": first["url"]}

        # 有些 API 返回 task_id，需要轮询
        task_id = data.get("id")

        if not task_id:
            return {"success": False, "error": "未获取到任务ID", "raw_response": data}

        # 轮询（最多 90 秒）
        for _ in range(45):
            time.sleep(2)
            status_resp = requests.get(
                f"{DEFAULT_API_BASE}/responses/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30
            )
            if status_resp.status_code == 200:
                sd = status_resp.json()
                status = sd.get("status", "")
                if status == "completed":
                    for item in sd.get("output", []):
                        if item.get("type") == "image":
                            return {"success": True, "image_url": item.get("url", ""), "task_id": task_id}
                    return {"success": False, "error": "生成完成但未找到图片"}
                elif status == "failed":
                    return {"success": False, "error": f"生成失败: {sd.get('error', {}).get('message', '未知错误')}"}

        return {"success": False, "error": "生成超时"}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时"}
    except Exception as e:
        return {"success": False, "error": f"生成失败: {str(e)}"}


# ─────────────────────────────────────────────
# 格式化输出
# ─────────────────────────────────────────────

def format_analyze_result(result: dict, saved: dict = None) -> str:
    if not result["success"]:
        return f"❌ 风格分析失败: {result['error']}"
    lines = ["✅ 风格分析完成"]
    if saved:
        name_part = f"（名称：{saved.get('style_name', '')}）" if saved.get('style_name') else ""
        lines.append(f"   风格编号：#{saved['style_id']} {name_part}  →  已保存")
    lines.append("")
    lines.append(f"📝 风格描述：\n{result.get('style_description', '无')}")
    return "\n".join(lines)


def format_generate_result(result: dict) -> str:
    if not result["success"]:
        return f"❌ 图片生成失败: {result['error']}"
    url = result.get("image_url", "")
    tid = result.get("task_id", "")
    out = ["✅ 图片生成完成", f"🖼️ {url}"]
    if tid:
        out.append(f"📋 任务ID：{tid}")
    return "\n".join(out)


def format_list_styles(records: list) -> str:
    if not records:
        return "📭 暂未保存任何风格"
    lines = ["📋 已保存的风格："]
    for r in records:
        name = r.get("style_name", "")
        name_str = f"【{name}】" if name else ""
        desc = r.get("style_description", "")[:40].replace("\n", " ")
        lines.append(f"  #{r['id']:03d} {name_str}  {desc}...")
        lines.append(f"        保存于 {r.get('saved_at', '')}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": """用法：
  提取并保存风格：python3 scripts/doubao_image_ops.py analyze <图片路径或URL> [--name=风格名称]
  生成图片：       python3 scripts/doubao_image_ops.py generate "<生图描述>" [--size 16:9]
  使用风格生图：   python3 scripts/doubao_image_ops.py use <风格编号或名称> "<生图描述>" [--size 16:9]
  查看风格列表：   python3 scripts/doubao_image_ops.py list
        """
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    command = sys.argv[1]

    # ── 提取 + 保存风格 ───────────────────────
    if command == "analyze":
        if len(sys.argv) < 3:
            print(json.dumps({"success": False, "error": "请提供图片路径或URL"}, ensure_ascii=False))
            sys.exit(1)

        image_path = sys.argv[2]
        prompt = None
        style_name = ""

        for arg in sys.argv[3:]:
            if arg.startswith("--name="):
                style_name = arg.split("=", 1)[1]
            elif not arg.startswith("--"):
                prompt = arg

        result = analyze_style(image_path, prompt)

        if result["success"] and "--no-save" not in sys.argv:
            saved = save_style(result["style_description"], source_image=image_path, style_name=style_name)
        else:
            saved = None

        if "--format" in sys.argv or "-f" in sys.argv:
            print(format_analyze_result(result, saved))
        else:
            out = {"success": result["success"]}
            if result["success"]:
                out["style_description"] = result["style_description"]
                if saved:
                    out["style_id"] = saved["style_id"]
                    out["style_path"] = saved["path"]
            else:
                out["error"] = result["error"]
            print(json.dumps(out, ensure_ascii=False, indent=2))

    # ── 纯文字生图 ─────────────────────────────
    elif command == "generate":
        if len(sys.argv) < 3:
            print(json.dumps({"success": False, "error": "请提供生图描述"}, ensure_ascii=False))
            sys.exit(1)

        user_prompt = sys.argv[2]
        size = "16:9"
        for arg in sys.argv[3:]:
            if arg.startswith("--size="):
                size = arg.split("=")[1]

        result = generate_image(user_prompt, size)

        if "--format" in sys.argv or "-f" in sys.argv:
            print(format_generate_result(result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

    # ── 指定风格生图 ───────────────────────────
    elif command == "use":
        if len(sys.argv) < 4:
            print(json.dumps({"success": False, "error": "请提供风格编号和生图描述"}, ensure_ascii=False))
            sys.exit(1)

        style_arg = sys.argv[2]
        user_prompt = sys.argv[3]
        size = "16:9"
        for arg in sys.argv[4:]:
            if arg.startswith("--size="):
                size = arg.split("=")[1]

        style_res = load_style(style_arg)
        if not style_res["success"]:
            print(json.dumps(style_res, ensure_ascii=False, indent=2))
            sys.exit(1)

        record = style_res["record"]
        fused = fuse_prompt(user_prompt, record["style_description"])

        result = generate_image(fused, size)

        if "--format" in sys.argv or "-f" in sys.argv:
            out_text = format_generate_result(result)
            if result["success"]:
                out_text += f"\n🎨 风格来源：#{record['id']}（{record.get('saved_at', '')}）"
            print(out_text)
        else:
            out = dict(result)
            out["style_id"] = record["id"]
            out["fused_prompt"] = fused
            print(json.dumps(out, ensure_ascii=False, indent=2))

    # ── 下载图片到本地 ─────────────────────────
    elif command == "download":
        if len(sys.argv) < 3:
            print(json.dumps({"success": False, "error": "请提供图片URL"}, ensure_ascii=False))
            sys.exit(1)

        image_url = sys.argv[2]
        output_path = sys.argv[3] if len(sys.argv) > 3 else ""

        from urllib.parse import urlparse
        parsed = urlparse(image_url)
        headers = {"User-Agent": "Mozilla/5.0"}
        if parsed.netloc:
            headers["Host"] = parsed.netloc

        resp = requests.get(image_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(json.dumps({"success": False, "error": f"下载失败 HTTP {resp.status_code}"}, ensure_ascii=False))
            sys.exit(1)

        if not output_path:
            ext = parsed.path.split(".")[-1] if "." in parsed.path else "jpg"
            output_path = os.path.join("/tmp", f"doubao_img_{int(time.time())}.{ext}")

        with open(output_path, "wb") as f:
            f.write(resp.content)

        print(json.dumps({"success": True, "local_path": output_path}, ensure_ascii=False, indent=2))

    # ── 列出已保存的风格 ───────────────────────
    elif command == "list":
        records = list_styles()
        if "--format" in sys.argv or "-f" in sys.argv:
            print(format_list_styles(records))
        else:
            print(json.dumps({"success": True, "styles": records}, ensure_ascii=False, indent=2))

    else:
        print(json.dumps({"success": False, "error": f"未知命令: {command}"}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
