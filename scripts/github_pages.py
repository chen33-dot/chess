"""Use the existing Git credential in memory; never print or persist it."""
import json
import subprocess
import sys
import urllib.request
import urllib.error

result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n', text=True, capture_output=True)
credential = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
secret = credential.get('password')
if not secret:
    raise SystemExit('No GitHub credential available for Pages API.')

def api(path, method='GET', data=None):
    request = urllib.request.Request('https://api.github.com/repos/chen33-dot/chess' + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization': 'Bearer ' + secret, 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'chess-pages-setup'}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {'message': json.loads(exc.read()).get('message', 'API request failed')}

if '--public' in sys.argv:
    status, repo = api('', 'PATCH', {'private': False})
    print('Repository visibility:', status, repo.get('visibility'), repo.get('message', ''))
status, page = api('/pages')
print('Pages:', status, json.dumps({k: page.get(k) for k in ('html_url', 'status', 'build_type', 'message')}, ensure_ascii=False))
if '--enable' in sys.argv and (status == 404 or (status == 200 and page.get('build_type') != 'workflow')):
    status, page = api('/pages', 'POST' if status == 404 else 'PUT', {'build_type': 'workflow'})
    print('Enable Pages:', status, json.dumps(page, ensure_ascii=False))
status, runs = api('/actions/runs?per_page=3')
print('Actions:', status)
for run in runs.get('workflow_runs', []):
    print(json.dumps({k: run.get(k) for k in ('name', 'status', 'conclusion', 'html_url', 'head_sha')}, ensure_ascii=False))
