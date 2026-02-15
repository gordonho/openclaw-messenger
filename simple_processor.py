#!/usr/bin/env python3
"""简单处理器 - 直接用 imsg 发送"""
import os, json, time, subprocess

INBOX = '/tmp/openclaw_inbox.json'

def read(f, d=[]):
    if os.path.exists(f):
        try:
            with open(f) as fp: return json.load(fp)
        except: pass
    return d

def write(f, d):
    with open(f, 'w') as fp: json.dump(d, fp, indent=2)

print("Started processor...")
processed = set()

while True:
    try:
        inbox = read(INBOX, [])
        for m in inbox:
            mid = m.get('id')
            tgt = m.get('target', 'hgdemail@icloud.com')
            if mid and mid not in processed and m.get('status') == 'pending':
                cnt = m.get('content', '')
                r = subprocess.run(['imsg','send','--to',tgt,'--text',cnt], capture_output=True, timeout=30)
                if r.returncode == 0:
                    print(f"Sent: {cnt[:20]}")
                    m['status'] = 'sent_to_openclaw'
                else:
                    print(f"Failed: {r.stderr}")
                    m['status'] = 'failed'
                processed.add(mid)
        write(INBOX, inbox)
        time.sleep(2)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)
