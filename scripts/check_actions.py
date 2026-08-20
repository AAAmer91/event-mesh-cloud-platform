import urllib.request
import json

req = urllib.request.Request(
    'https://api.github.com/repos/AAAmer91/event-mesh-cloud-platform/actions/runs?per_page=5',
    headers={'User-Agent': 'Python'}
)
res = json.loads(urllib.request.urlopen(req).read())
for r in res['workflow_runs']:
    print(f"[{r['id']}] {r['name']} -> status: {r['status']}, conclusion: {r['conclusion']} (commit: {r['head_sha'][:7]})")
