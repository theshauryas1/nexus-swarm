import requests
import re

url = "https://nexusswarm-frontend-669943047856.us-central1.run.app"
r = requests.get(url)
print("Frontend Status:", r.status_code)
scripts = re.findall(r'src="(/assets/[^"]+)"', r.text)
print("Scripts found:", scripts)
for s in scripts:
    js_url = url + s
    r_js = requests.get(js_url)
    print("JS:", s, "Status:", r_js.status_code)
    matches = re.findall(r'https?://[a-zA-Z0-9\-\.]+\.run\.app', r_js.text)
    print("Found run.app URLs in JS:", set(matches))
    ws_matches = re.findall(r'wss?://[a-zA-Z0-9\-\.]+\.run\.app', r_js.text)
    print("Found ws URLs in JS:", set(ws_matches))
