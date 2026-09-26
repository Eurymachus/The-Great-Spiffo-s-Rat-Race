"""Browser reproduction: python tests/javascript/navigation_fixture_server.py.

Uses content-hashed assets and Cloudflare's observed self-removing script shape.
The old route serves the original staging commit; fixed serves the working file.
This isolated local fixture does not read or change the application database.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import hashlib
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
ASSET = 'apps/website/registry/static/registry/page_navigation.js'
OLD = subprocess.check_output(['git', 'show', '41f91309:' + ASSET], cwd=ROOT)
NEW = (ROOT / ASSET).read_bytes()
ASSETS = {f'/static/page_navigation.{hashlib.md5(data).hexdigest()[:12]}.js': data for data in (OLD, NEW)}
DECODER = '/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js'

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        if path in ASSETS:
            body, mime = ASSETS[path], 'text/javascript'
        elif path == DECODER:
            body, mime = b'document.currentScript.remove();', 'text/javascript'
        else:
            mode = 'old' if path.startswith('/old/') else 'fixed'
            data = OLD if mode == 'old' else NEW
            src = next(key for key, value in ASSETS.items() if value == data)
            body = f'''<!doctype html><title>Navigation regression fixture</title>
<script defer src="{src}"></script>
<header>Document token: <span id="token">{uuid.uuid4()}</span></header>
<main id="main-content" data-soft-navigation="on" data-navigation-user="test">
<h1>{mode}: {path}</h1>
<a href="/{mode}/rules/">Rules</a> <a href="/{mode}/home/">Home</a>
<a href="/cdn-cgi/l/email-protection#45363035352a37310531223637376b262a28"><span data-cfemail="53202623233c21271327342021217d303c3e">Protected email</span></a>
</main><script data-cfasync="false" src="{DECODER}"></script>'''.encode()
            mime = 'text/html'
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    print('Fixture: http://127.0.0.1:8766/old/ and /fixed/', flush=True)
    HTTPServer(('127.0.0.1', 8766), Handler).serve_forever()
