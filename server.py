import http.server
import socketserver
import threading
import os
import json
import socket
import time
import uuid
from urllib.parse import urlparse, unquote

STORAGE_DIR = os.path.join(os.path.expanduser("~"), "FileTransferReceived")
os.makedirs(STORAGE_DIR, exist_ok=True)

HTML_PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>File Transfer</title>
<style>
body{font-family:sans-serif;background:#111;color:#eee;padding:20px;max-width:600px;margin:auto;}
h1{color:#4caf50;}
.box{background:#222;padding:15px;border-radius:10px;margin-bottom:15px;}
input[type=file]{margin:10px 0;color:#eee;}
button{background:#4caf50;color:#fff;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-size:16px;}
li{margin:6px 0;}
a{color:#4caf50;text-decoration:none;}
</style>
</head>
<body>
<h1>File Transfer</h1>
<div class="box">
<h3>رفع ملف (إرسال إلى هذا الجهاز)</h3>
<form method="POST" action="/upload" enctype="multipart/form-data">
<input type="file" name="file" required>
<br><button type="submit">رفع</button>
</form>
</div>
<div class="box">
<h3>الملفات المستلمة</h3>
<ul id="files"></ul>
</div>
<script>
async function loadFiles(){
  const res = await fetch('/list');
  const data = await res.json();
  const ul = document.getElementById('files');
  ul.innerHTML = '';
  data.files.forEach(f=>{
    const li = document.createElement('li');
    li.innerHTML = '<a href="/download/' + encodeURIComponent(f) + '">' + f + '</a>';
    ul.appendChild(li);
  });
}
loadFiles();
setInterval(loadFiles, 3000);
</script>
</body>
</html>"""


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        body = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/":
            self._send(200, HTML_PAGE)
        elif path == "/list":
            files = sorted(os.listdir(STORAGE_DIR))
            self._send(200, json.dumps({"files": files}), "application/json")
        elif path.startswith("/download/"):
            name = os.path.basename(path[len("/download/"):])
            fpath = os.path.join(STORAGE_DIR, name)
            if os.path.isfile(fpath):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", 'attachment; filename="%s"' % name)
                self.send_header("Content-Length", str(os.path.getsize(fpath)))
                self.end_headers()
                with open(fpath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._send(404, "Not found")
        else:
            self._send(404, "Not found")

    def do_POST(self):
        if urlparse(self.path).path != "/upload":
            self._send(404, "Not found")
            return
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            self._send(400, "Bad request")
            return
        boundary = ctype.split("boundary=")[-1].encode()
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)
        parts = data.split(b"--" + boundary)
        saved = None
        for part in parts:
            if b"Content-Disposition" not in part:
                continue
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            headers = part[:header_end].decode(errors="ignore")
            body = part[header_end + 4:]
            if body.endswith(b"\r\n"):
                body = body[:-2]
            if 'filename="' in headers:
                filename = headers.split('filename="')[1].split('"')[0]
                if not filename:
                    continue
                filename = os.path.basename(filename)
                unique = "%s_%s" % (uuid.uuid4().hex[:6], filename)
                fpath = os.path.join(STORAGE_DIR, unique)
                with open(fpath, "wb") as f:
                    f.write(body)
                saved = unique
        if saved:
            self._send(200, json.dumps({"status": "ok", "saved": saved}), "application/json")
        else:
            self._send(400, json.dumps({"status": "error"}), "application/json")


class FileServer:
    def __init__(self, port=8000):
        self.port = port
        self.httpd = None
        self.thread = None

    def start(self):
        self.httpd = socketserver.ThreadingTCPServer(("0.0.0.0", self.port), Handler)
        self.httpd.allow_reuse_address = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return get_local_ip(), self.port

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


if __name__ == "__main__":
    ip, port = FileServer(8000).start()
    print("Server running: http://%s:%s" % (ip, port))
    print("Storage folder: %s" % STORAGE_DIR)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped")
