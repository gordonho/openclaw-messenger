"""
OpenClaw Web Messenger - 模仿飞书插件与OpenClaw通信
通过 WebSocket 和 REST API 与 OpenClaw Gateway 通信

运行: python3 app.py
访问: http://localhost:5001

配置:
- 本地运行: 默认连接 localhost:18789
- 远程运行: 需要设置环境变量 OPENCLAW_URL
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'openclaw-web-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 配置
GATEWAY_URL = os.environ.get('OPENCLAW_URL', 'http://localhost:18789')
GATEWAY_TOKEN = os.environ.get('OPENCLAW_TOKEN', '')

# 消息历史
MESSAGES_FILE = os.path.expanduser('~/.openclaw/web_messages.json')

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_message(msg_type, content, status="sent"):
    messages = load_messages()
    messages.insert(0, {
        'type': msg_type,
        'content': content,
        'status': status,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    messages = messages[:100]
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

def send_to_openclaw_via_api(message: str) -> dict:
    """通过 Gateway API 发送消息"""
    import urllib.request
    
    headers = {'Content-Type': 'application/json'}
    if GATEWAY_TOKEN:
        headers['Authorization'] = f'Bearer {GATEWAY_TOKEN}'
    
    data = json.dumps({"message": message}).encode('utf-8')
    
    endpoints = [
        f"{GATEWAY_URL}/api/sessions/main/send",
        f"{GATEWAY_URL}/api/messages",
    ]
    
    for endpoint in endpoints:
        try:
            req = urllib.request.Request(endpoint, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=15) as response:
                return {"success": True, "endpoint": endpoint}
        except Exception as e:
            continue
    
    return {"success": False, "error": f"无法连接到 OpenClaw Gateway ({GATEWAY_URL})"}

def send_via_imessage(message: str) -> dict:
    """通过 iMessage 发送"""
    import subprocess
    target = os.environ.get('IMESSAGE_TARGET', 'hgdemail@icloud.com')
    try:
        result = subprocess.run(
            ["imsg", "send", target, message],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return {"success": True, "method": "imessage"}
        else:
            return {"success": False, "error": result.stderr or "iMessage发送失败"}
    except FileNotFoundError:
        return {"success": False, "error": "imsg命令未找到（仅本地可用）"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/')
def index():
    messages = load_messages()
    return render_template('index.html', messages=messages, gateway_url=GATEWAY_URL)

@app.route('/api/send', methods=['POST'])
def send_message():
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"success": False, "error": "消息不能为空"})
    
    # 尝试通过 API 发送
    result = send_to_openclaw_via_api(message)
    
    # 如果失败，尝试 iMessage
    if not result.get("success"):
        result = send_via_imessage(message)
    
    # 保存消息记录
    save_message("sent", message, "成功" if result.get("success") else "失败")
    
    # 通过 WebSocket 通知前端
    socketio.emit('new_message', {
        'type': 'sent',
        'content': message,
        'status': '成功' if result.get("success") else '失败'
    })
    
    return jsonify(result)

@app.route('/api/messages', methods=['GET'])
def get_messages():
    return jsonify(load_messages())

@app.route('/api/status', methods=['GET'])
def get_status():
    """检查 OpenClaw 连接状态"""
    import urllib.request
    try:
        req = urllib.request.Request(f"{GATEWAY_URL}/api/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            return jsonify({"status": "connected", "url": GATEWAY_URL})
    except Exception as e:
        return jsonify({
            "status": "disconnected", 
            "url": GATEWAY_URL,
            "error": str(e),
            "hint": "在远程环境需要配置 OPENCLAW_URL 环境变量"
        })

@socketio.on('connect')
def handle_connect():
    emit('connected', {'data': 'Connected to OpenClaw Web'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
    
    print("🚀 OpenClaw Web Messenger 启动中...")
    print(f"📍 访问 http://localhost:5001")
    print(f"🔗 Gateway: {GATEWAY_URL}")
    print("📡 WebSocket 已启用")
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
