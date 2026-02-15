"""
OpenClaw Web Messenger - 文件中转版本
通过本地文件与 OpenClaw 通信

工作原理:
- 发送消息 → 写入 inbox.json
- 接收回复 → 读取 outbox.json
- 定时轮询获取回复

运行: python3 app.py
访问: http://localhost:5001
"""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import json
from datetime import datetime
import time
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'openclaw-web-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 中转文件路径
INBOX_FILE = '/tmp/openclaw_inbox.json'
OUTBOX_FILE = '/tmp/openclaw_outbox.json'

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

def add_to_inbox(message, target='hgdemail@icloud.com'):
    """添加消息到收件箱"""
    inbox = read_json_file(INBOX_FILE, [])
    inbox.insert(0, {
        'id': f"msg_{int(time.time()*1000)}",
        'content': message,
        'target': target,  # 目标用户
        'timestamp': datetime.now().isoformat(),
        'status': 'pending'
    })
    write_json_file(INBOX_FILE, inbox)

def get_from_outbox():
    """从发件箱获取回复"""
    return read_json_file(OUTBOX_FILE, [])

def mark_processed(msg_id):
    """标记消息已处理"""
    inbox = read_json_file(INBOX_FILE, [])
    for msg in inbox:
        if msg.get('id') == msg_id:
            msg['status'] = 'processed'
    write_json_file(INBOX_FILE, inbox)

# 消息历史
MESSAGES_FILE = os.path.expanduser('~/.openclaw/web_messages.json')

def load_messages():
    return read_json_file(MESSAGES_FILE, [])

def save_message(msg_type, content, status="sent", target=""):
    messages = load_messages()
    messages.insert(0, {
        'type': msg_type,
        'content': content,
        'status': status,
        'target': target,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    messages = messages[:100]
    write_json_file(MESSAGES_FILE, messages)

# ============ API 接口 ============

@app.route('/')
def index():
    messages = load_messages()
    return render_template('index.html', messages=messages)

@app.route('/api/send', methods=['POST'])
def send_message():
    """发送消息到 OpenClaw - 直接通过 imsg 发送"""
    import subprocess
    
    data = request.get_json()
    message = data.get('message', '').strip()
    target = data.get('target', '').strip() or 'hgdemail@icloud.com'
    
    if not message:
        return jsonify({"success": False, "error": "消息不能为空"})
    
    # 直接通过 imsg 发送
    try:
        result = subprocess.run(
            ["imsg", "send", "--to", target, "--text", message],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            status_msg = "已发送"
        else:
            status_msg = "失败: " + (result.stderr or "未知错误")
    except Exception as e:
        status_msg = "错误: " + str(e)
    
    # 保存到历史
    save_message("sent", message, status_msg, target)
    
    # 通知前端
    socketio.emit('new_message', {
        'type': 'sent',
        'content': message,
        'status': status_msg
    })
    
    return jsonify({"success": result.returncode == 0, "message": status_msg, "target": target})

@app.route('/api/poll', methods=['GET'])
def poll_messages():
    """轮询获取回复"""
    outbox = get_from_outbox()
    return jsonify(outbox)

@app.route('/api/messages', methods=['GET'])
def get_messages():
    """获取当前用户的消息历史"""
    user = request.args.get('user', '')
    all_messages = load_messages()
    
    if user:
        # 过滤当前用户的消息
        messages = [m for m in all_messages if m.get('target') == user or m.get('user') == user]
    else:
        messages = all_messages
    
    return jsonify(messages)

@app.route('/api/status', methods=['GET'])
def status():
    inbox_count = len(read_json_file(INBOX_FILE, []))
    outbox_count = len(get_from_outbox())
    return jsonify({
        "status": "running",
        "mode": "file_relay",
        "inbox_count": inbox_count,
        "outbox_count": outbox_count
    })

# WebSocket
@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    pass

# 后台任务：轮询 outbox 并推送
def background_poller():
    """后台轮询回复"""
    last_outbox = []
    while True:
        time.sleep(2)
        try:
            outbox = get_from_outbox()
            if outbox != last_outbox and outbox:
                # 有新回复
                for msg in outbox:
                    if msg.get('type') == 'received':
                        save_message("received", msg.get('content'), "已收到")
                        socketio.emit('new_message', {
                            'type': 'received',
                            'content': msg.get('content')
                        })
                last_outbox = outbox
        except Exception as e:
            print(f"Polling error: {e}")
            pass

if __name__ == '__main__':
    # 启动后台轮询线程
    poller_thread = threading.Thread(target=background_poller, daemon=True)
    poller_thread.start()
    
    os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
    
    print("🚀 OpenClaw Web Messenger (文件中转版)")
    print(f"📍 访问 http://localhost:5001")
    print(f"📬 INBOX:  {INBOX_FILE}")
    print(f"📫 OUTBOX: {OUTBOX_FILE}")
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
