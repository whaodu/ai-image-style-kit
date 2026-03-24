#!/usr/bin/env python3
"""
飞书发送图片脚本
用法：
  python3 feishu_send_image.py <图片URL或本地路径> [飞书access_token]
"""

import sys
import os
import requests
import json

# 飞书 API 配置
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

# 从环境变量获取 token（优先）或命令行参数
def get_token(token_from_arg: str = None) -> str:
    if token_from_arg:
        return token_from_arg
    token = os.environ.get("FEISHU_ACCESS_TOKEN", "")
    if token:
        return token
    # 尝试从 app_id/app_secret 自动获取
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if app_id and app_secret:
        resp = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=10
        )
        data = resp.json()
        if data.get("code") == 0:
            return data["tenant_access_token"]
    raise ValueError("未找到飞书 access_token，请设置 FEISHU_ACCESS_TOKEN 或 FEISHU_APP_ID+FEISHU_APP_SECRET 环境变量")


def download_image(source: str) -> bytes:
    """下载远程图片或读取本地图片"""
    if source.startswith(("http://", "https://")):
        # 提取 host 头（TOS 签名 URL 需要）
        from urllib.parse import urlparse
        parsed = urlparse(source)
        headers = {"User-Agent": "Mozilla/5.0"}
        if parsed.netloc:
            headers["Host"] = parsed.netloc
        resp = requests.get(source, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise ValueError(f"下载失败 HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.content
    else:
        with open(source, "rb") as f:
            return f.read()


def upload_to_feishu(image_data: bytes, filename: str, token: str) -> str:
    """
    上传图片到飞书，返回 image_key
    POST https://open.feishu.cn/open-apis/im/v1/images
    """
    url = f"{FEISHU_API_BASE}/im/v1/images"
    headers = {
        "Authorization": f"Bearer {token}",
    }
    files = {
        "image_type": (None, "message"),
        "image": (filename, image_data, "image/jpeg"),
    }
    resp = requests.post(url, headers=headers, files=files, timeout=30)
    if resp.status_code != 200:
        raise ValueError(f"上传失败 HTTP {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    if data.get("code") != 0:
        raise ValueError(f"上传失败: {data.get('msg', data)}")
    return data["data"]["image_key"]


def send_image_message(image_key: str, token: str, receive_id: str = None) -> dict:
    """
    发送图片消息
    POST https://open.feishu.cn/open-apis/im/v1/messages
    """
    url = f"{FEISHU_API_BASE}/im/v1/messages?receive_id_type=open_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "receive_id": receive_id or os.environ.get("FEISHU_USER_OPEN_ID", "ou_3faabba5410648e6cd64dd2d4df70b1d"),
        "msg_type": "image",
        "content": json.dumps({"image_key": image_key})
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise ValueError(f"发送失败 HTTP {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    if data.get("code") != 0:
        raise ValueError(f"发送失败: {data.get('msg', data)}")
    return data["data"]


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "用法：python3 feishu_send_image.py <图片URL或本地路径> [飞书access_token]"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    source = sys.argv[1]
    token = get_token(sys.argv[2] if len(sys.argv) > 2 else None)

    print(f"📥 下载图片: {source[:80]}...")
    image_data = download_image(source)
    print(f"📤 上传图片到飞书...")
    image_key = upload_to_feishu(image_data, "image.jpg", token)
    print(f"📨 发送图片消息...")
    result = send_image_message(image_key, token)
    print(json.dumps({"success": True, "image_key": image_key, "result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
