#!/usr/bin/env python3
"""
OpenClaw 文件中转处理器 - 使用 OpenClaw CLI
读取 inbox.json，通过 openclaw agent 命令发送消息给 OpenClaw
"""

import os
import json
import time
import subprocess
from datetime import datetime

# 中转文件路径
INBOX_FILE = '/tmp/openclaw_inbox.json'
OUTBOX_FILE = '/tmp/openclaw_outbox.json'
POLL_INTERVAL = 2
OPENCLAW_BIN = os.environ.get('OPENCLAW_BIN', '/Users/gordon/.nvm/versions/node/v22.12.0/bin/openclaw')

def read_json_file(filepath, default=[]):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default

def write_json_file(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_via_openclaw(message: str, target: str = "hgdemail@icloud.com") -> bool:
    """通过 OpenClaw CLI 发送消息"""
    try:
        result = subprocess.run(
            [
                OPENCLAW_BIN, 
                "agent",
                "--channel", "imessage",
                "--to", target,
                "--message", message,
                "--deliver"
            ],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("📬 OpenClaw 文件中转处理器 (CLI版) 启动")
    print(f"📂 监听: {INBOX_FILE}")
    print(f"🔧 CLI: {OPENCLAW_BIN}")
    print("-" * 40)
    
    processed_ids = set()
    
    while True:
        try:
            inbox = read_json_file(INBOX_FILE, [])
            
            for msg in inbox:
                msg_id = msg.get('id')
                if msg_id and msg_id not in processed_ids and msg.get('status') == 'pending':
                    content = msg.get('content', '')
                    
                    # 通过 OpenClaw CLI 发送
                    if send_via_openclaw(content):
                        print(f"✅ 已发送: {content[:30]}...")
                        msg['status'] = 'sent_to_openclaw'
                    else:
                        print(f"❌ 发送失败: {content[:30]}...")
                        msg['status'] = 'failed'
                    
                    processed_ids.add(msg_id)
            
            write_json_file(INBOX_FILE, inbox)
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n👋 处理器已停止")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
