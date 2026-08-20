import json
import urllib.request

req = urllib.request.Request(
    "https://api.github.com/repos/AAAmer91/event-mesh-cloud-platform/actions/runs/32428723363/jobs",
    headers={"User-Agent": "Python"},
)
res = json.loads(urllib.request.urlopen(req).read())
for j in res["jobs"]:
    print(f"--- Job: {j['name']} ({j['status']} / {j['conclusion']}) ---")
    for s in j.get("steps", []):
        print(f"  [{s['number']}] {s['name']} -> {s['conclusion']}")
