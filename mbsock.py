import requests
from websocket import create_connection
import json

def get_cdn(vid, seg):
    ws = create_connection('wss://v.myself-bbs.com/ws')
    payload = {
        'tid': vid,
        'vid': seg,
        'id': '',
    }
    ws.send(json.dumps(payload))
    r = ws.recv()
    try:
        ret = json.loads(r)['video']
    except Exception:
        print("[ERROR] Unable to get CDN:")
        print(r)
    return f"https:{ret}"

def is_cdn_alive(vid):
    cdn = get_cdn(vid, '001')
    try:
        res = requests.get(cdn, timeout=(3,3))
        if res.status_code == 200:
            return res.content
    except Exception:
        pass
    return None

def get_available_cdn():
    ret = []
    for i in range(100):
        try:
            host = f"https://vpx{i:02d}.myself-bbs.com/"
            res = requests.get(host, timeout=(3,3))
            if res.status_code == 200:
                print(host)
                ret.append(host)
        except Exception:
            pass
    return ret

# check alive animes
# animes = []
# checked = set()
# for node in animes:
#     try:
#         if node['href'][:7] != 'thread-' or not node['title']:
#             continue
#     except Exception:
#         continue
#     vid = node['href'].split('-')[1]
#     if vid in checked:
#         continue
#     checked.add(vid)
#     print(node['title'], 1 if is_cdn_alive(vid) else 0)