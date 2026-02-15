"""
OpenClaw 消息发送 Web 应用
运行: python3 app.py
访问: http://localhost:5001

注意: OpenClaw Gateway 不直接暴露消息发送API
本应用提供两种模式:
1. 本地模式: 通过 iMessage CLI 发送 (默认)
2. 远程模式: 需要配置 Tailscale 或 VPN 连接本地 Gateway
"""

from flask import Flask, render_template, request, jsonify
import os
import json
import subprocess
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'openclaw-web-secret-key'

# 消息历史文件
HISTORY_FILE = os.path.expanduser('~/.openclaw/message_history.json')

def load_history():
    """加载消息历史"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(message, channel, status):
    """保存消息历史"""
    history = load_history()
    history.insert(0, {
        'message': message,
        'channel': channel,
        'status': status,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    history = history[:50]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def send_via_imessage(message: str, target: str = None) -> dict:
    """通过 imessage CLI 发送消息"""
    # 默认发送到自己的邮箱
    if not target:
        target = "hgdemail@icloud.com"
    
    try:
        result = subprocess.run(
            ["imsg", "send", target, message],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return {"success": True, "response": "消息已发送"}
        else:
            return {"success": False, "error": result.stderr or "发送失败"}
    except FileNotFoundError:
        return {"success": False, "error": "imsg 命令未找到，请确保已配置 iMessage"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_to_openclaw(message: str, target: str = None, channel: str = "imessage") -> dict:
    """发送消息到 OpenClaw"""
    # 根据渠道选择发送方式
    if channel == "imessage":
        return send_via_imessage(message, target)
    else:
        return {"success": False, "error": f"暂不支持频道: {channel}"}

@app.route('/')
def index():
    """主页"""
    history = load_history()
    return render_template('index.html', history=history)

@app.route('/api/send', methods=['POST'])
def send_message():
    """发送消息 API"""
    data = request.get_json()
    message = data.get('message', '').strip()
    channel = data.get('channel', 'imessage')
    target = data.get('target', '')
    
    if not message:
        return jsonify({"success": False, "error": "消息不能为空"})
    
    result = send_to_openclaw(message, target, channel)
    save_history(message, channel, "成功" if result["success"] else "失败")
    
    return jsonify(result)

@app.route('/api/history', methods=['GET'])
def get_history():
    """获取消息历史"""
    return jsonify(load_history())

if __name__ == '__main__':
    os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
    
    print("🚀 OpenClaw Web 应用启动中...")
    print("📍 访问 http://localhost:5001")
    print("📱 当前通过 iMessage 发送消息")
    app.run(host='0.0.0.0', port=5001, debug=True)
