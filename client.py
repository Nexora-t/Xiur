import os
import mimetypes
import urllib.request
import uuid


def send_file(target_ip, port, filepath):
    if not os.path.isfile(filepath):
        raise FileNotFoundError(filepath)
    filename = os.path.basename(filepath)
    boundary = uuid.uuid4().hex

    with open(filepath, "rb") as f:
        file_data = f.read()

    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    body = bytearray()
    body += ("--%s\r\n" % boundary).encode()
    body += ('Content-Disposition: form-data; name="file"; filename="%s"\r\n' % filename).encode()
    body += ("Content-Type: %s\r\n\r\n" % ctype).encode()
    body += file_data
    body += ("\r\n--%s--\r\n" % boundary).encode()

    url = "http://%s:%s/upload" % (target_ip, port)
    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", "multipart/form-data; boundary=%s" % boundary)
    req.add_header("Content-Length", str(len(body)))

    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.read().decode(errors="ignore")
