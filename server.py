#!/usr/bin/env python3
"""
Minimal static + API server for the codebase-modeler artifact viewer.

Serves:
  /                      -> viewer/index.html
  /<static>              -> viewer/<static>  (index.html, app.js, styles.css, vendor/*)
  /api/repos             -> JSON list of repos that have modeled artifacts in output/
  /api/content?repo&doc  -> raw markdown text of output/<repo>/<doc>

Standard library only. Run:  python3 server.py [port]
"""
import json
import os
import re
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(ROOT, "viewer")
OUTPUT_DIR = os.path.join(ROOT, "output")

# The six artifacts the viewer can display, keyed by the exact on-disk filename.
ALLOWED_DOCS = {
    "Specification.md",
    "ActivityDiagram.md",
    "UseCaseModel.md",
    "ClassModel.md",
    "DomainModel.md",
    "DatabaseModel.md",
}

REPO_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


def list_repos():
    """Return sorted names of subdirectories under output/ holding at least one artifact."""
    if not os.path.isdir(OUTPUT_DIR):
        return []
    repos = []
    for name in sorted(os.listdir(OUTPUT_DIR)):
        if name.startswith("."):
            continue
        path = os.path.join(OUTPUT_DIR, name)
        if not os.path.isdir(path):
            continue
        present = {f for f in os.listdir(path) if f in ALLOWED_DOCS}
        if present:
            repos.append(name)
    return repos


def safe_resolve(base, *parts):
    """Join parts onto base and refuse to escape the base directory."""
    candidate = os.path.abspath(os.path.join(base, *parts))
    base_abs = os.path.abspath(base)
    if candidate != base_abs and not candidate.startswith(base_abs + os.sep):
        return None
    return candidate


class Handler(BaseHTTPRequestHandler):
    server_version = "ArtifactViewer/1.0"

    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _send(self, code, body, ctype, extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, obj, code=200):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def _send_static(self, rel):
        path = safe_resolve(STATIC_DIR, rel)
        if path is None or not os.path.isfile(path):
            self._send(404, "not found", "text/plain")
            return
        ctype = MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream")
        with open(path, "rb") as fh:
            self._send(200, fh.read(), ctype)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        if path in ("/", "/index.html"):
            self._send_static("index.html")
            return

        if path == "/api/repos":
            self._send_json(list_repos())
            return

        if path == "/api/content":
            q = urllib.parse.parse_qs(parsed.query)
            repo = q.get("repo", [""])[0]
            doc = q.get("doc", [""])[0]
            if not REPO_NAME_RE.match(repo) or doc not in ALLOWED_DOCS:
                self._send_json({"error": "bad repo or doc"}, 400)
                return
            fpath = safe_resolve(OUTPUT_DIR, repo, doc)
            if fpath is None or not os.path.isfile(fpath):
                self._send_json({"error": "not found"}, 404)
                return
            with open(fpath, "r", encoding="utf-8") as fh:
                self._send(200, fh.read(), "text/plain; charset=utf-8")
            return

        # Any other path is treated as a static asset under viewer/.
        rel = path.lstrip("/")
        self._send_static(rel)

    do_HEAD = do_GET


def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    elif os.environ.get("PORT", "").isdigit():
        port = int(os.environ["PORT"])
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Artifact viewer running at:  http://127.0.0.1:{port}/")
    print(f"  output dir : {OUTPUT_DIR}")
    print(f"  repos found: {', '.join(list_repos()) or '(none yet)'}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        httpd.server_close()


if __name__ == "__main__":
    main()
