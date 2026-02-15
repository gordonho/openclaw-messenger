"""
OpenClaw 消息中转服务
将 Web App 的消息直接转发给 OpenClaw

工作原理:
1. Web App 发送消息到本服务 (/api/send)
2. 本服务调用 OpenClaw 的消息接口
3. 响应通过 WebSocket 推送给 Web App

运行: python3 relay.py
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import os
import json
import subprocess
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'openclaw-relay-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 消息队列文件
QUEUE_FILE = '/tmp/openclaw_web_queue.json'
RESPONSE_FILE = '/tmp/openclaw_web_response.json'

def read_queue():
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def write_queue(data):
    with open(QUEUE_FILE, 'w') as f:
        json.dump(data, f)

def queue_message(msg_type, content):
    queue = read_queue()
    queue.insert(0, {
        'type': msg_type,
        'content': content,
        'timestamp': datetime.now().isoformat()
    })
    queue = queue[:50]
    write_queue(queue)

def send_to_openclaw(message: str) -> dict:
    """通过 imsg 发送消息给 OpenClaw"""
    try:
        # 使用 imsg 发送消息到自己，OpenClaw 会自动接收
        result = subprocess.run(
            ["imsg", "send", "--to", "hgdemail@icloud.com", "--text", message],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return {"success": True}
        return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============ API 接口 ============

@app.route('/api/send', methods=['POST'])
def send_message():
    """接收 Web App 发送的消息"""
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"success": False, "error": "消息不能为空"})
    
    # 加入消息队列
    queue_message('sent', message)
    
    # 发送到 OpenClaw (通过 iMessage)
    result = send_to_openclaw(message)
    
    # 通知前端
    socketio.emit('new_message', {
        'type': 'sent',
        'content': message,
        'status': '发送中' if result['success'] else '失败'
    })
    
    return jsonify(result)

@app.route('/api/poll', methods=['GET'])
def poll_messages():
    """前端轮询获取新消息"""
    queue = read_queue()
    # 返回最近的消息
    return jsonify(queue[:20])

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'running',
        'mode': 'relay',
        'queue_file': QUEUE_FILE
    })

# WebSocket
@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'connected to relay'})

if __name__ == '__main__':
    print("🔄 OpenClaw 消息中转服务")
    print(f"📍 访问 http://localhost:5002")
    print("💬 消息将直接发送给 OpenClaw (通过 iMessage)")
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)
