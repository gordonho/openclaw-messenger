"""
OpenClaw 消息发送 Web 应用
运行: python3 app.py
访问: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify, session
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
    # 只保留最近50条
    history = history[:50]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def send_to_openclaw(message: str, target: str = None, channel: str = "imessage") -> dict:
    """发送消息到 OpenClaw"""
    gateway_url = os.environ.get("OPENCLAW_URL", "http://localhost:3000")
    
    data = {
        "channel": channel,
        "message": message
    }
    if target:
        data["target"] = target
    
    cmd = [
        "curl", "-s",
        "-X", "POST",
        f"{gateway_url}/api/messages",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {
            "success": result.returncode == 0,
            "response": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

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
    
    # 保存历史
    save_history(message, channel, "成功" if result["success"] else "失败")
    
    return jsonify(result)

@app.route('/api/history', methods=['GET'])
def get_history():
    """获取消息历史"""
    return jsonify(load_history())

if __name__ == '__main__':
    # 确保模板目录存在
    os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
    
    print("🚀 OpenClaw Web 应用启动中...")
    print("📍 访问 http://localhost:5000")
    app.run(host='0.0.0.0', port=5001, debug=True)
