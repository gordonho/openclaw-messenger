#!/usr/bin/env python3
"""
OpenClaw 消息发送工具
用法:
    python send_to_openclaw.py "消息内容"
    echo "消息内容" | python send_to_openclaw.py --stdin
"""

import argparse
import json
import os
import sys
import subprocess

def get_gateway_url():
    """获取 OpenClaw Gateway URL"""
    # 默认本地网关
    return os.environ.get("OPENCLAW_URL", "http://localhost:3000")

def send_message(message: str, channel: str = "imessage") -> bool:
    """发送消息到 OpenClaw"""
    gateway_url = get_gateway_url()
    
    # 构建请求
    cmd = [
        "curl",
        "-s",
        "-X", "POST",
        f"{gateway_url}/api/messages",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "channel": channel,
            "message": message,
            "target": "hgdemail@icloud.com"  # 默认发送给自己
        })
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ 消息已发送: {message}")
            return True
        else:
            print(f"❌ 发送失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="发送消息到 OpenClaw")
    parser.add_argument("message", nargs="?", help="要发送的消息")
    parser.add_argument("--stdin", action="store_true", help="从标准输入读取消息")
    parser.add_argument("--channel", default="imessage", help="消息渠道 (默认: imessage)")
    
    args = parser.parse_args()
    
    # 获取消息内容
    message = args.message
    if args.stdin:
        message = sys.stdin.read().strip()
    
    if not message:
        parser.print_help()
        sys.exit(1)
    
    # 发送消息
    success = send_message(message, args.channel)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
