from flask import Flask, jsonify, request, abort
import os
import tempfile

app = Flask(__name__)

# Require SECRET env var at startup (fail fast)
secKey = os.getenv("SECRET")
if not secKey:
    raise RuntimeError("Environment variable SECRET must be set before starting the app")

ONLINE_FILE = "onlineAddrs"
REQUESTED_FILE = "requestedFile.txt"
CONTENT_FILE = "fileContent.txt"

MAX_CONTENT_BYTES = 2 * 1024 * 1024  # 2 MB limit for file content

@app.before_request
def check_auth():
    key = request.headers.get("X-Auth-Key")
    if key != secKey:
        abort(403)

def read_addrs():
    if not os.path.exists(ONLINE_FILE):
        return []
    with open(ONLINE_FILE, "r") as f:
        addrs = [line.strip() for line in f.readlines() if line.strip()]
    # deduplicate while preserving order
    seen = set()
    unique = []
    for a in addrs:
        if a not in seen:
            seen.add(a)
            unique.append(a)
    return unique

def write_addrs(addrs):
    # atomic write
    dirpath = os.path.dirname(os.path.abspath(ONLINE_FILE)) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(addrs))
        os.replace(tmp, ONLINE_FILE)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

@app.route("/addrs-add", methods=["GET", "POST"])
def add():
    incoming = request.remote_addr or ""
    addrs = read_addrs()
    if incoming and incoming not in addrs:
        addrs.append(incoming)
        write_addrs(addrs)
    return jsonify({"status": "OK", "added": incoming}), 200

@app.route("/addrs-remove", methods=["GET", "POST"])
def remove():
    incoming = request.remote_addr or ""
    addrs = read_addrs()
    if incoming in addrs:
        addrs.remove(incoming)
        write_addrs(addrs)
        return jsonify({"status": "Removed", "addr": incoming}), 200
    return jsonify({"status": "NotFound", "addr": incoming}), 200

@app.route("/clear-index", methods=["POST", "GET"])
def clear():
    # clear file atomically
    write_addrs([])
    return jsonify({"status": "Cleared"}), 200

@app.route("/addrs", methods=["GET"])
def returnAddrs():
    addrs = read_addrs()
    return jsonify(addrs), 200

@app.route("/client-request", methods=["POST"])
def send():
    data = request.get_json(silent=True)
    if not data:
        abort(400, "JSON body required")
    # Accept legacy keys 'file' or 'fileName'
    fileName = data.get("file") or data.get("fileName")
    if not fileName or not isinstance(fileName, str):
        abort(400, "file name required")
    # sanitize fileName a bit (no path separators)
    if "/" in fileName or "\\" in fileName:
        abort(400, "invalid file name")
    # write filename atomically
    fd, tmp = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w") as f:
            f.write(fileName)
        os.replace(tmp, REQUESTED_FILE)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
    return jsonify("Request sent... Awaiting response"), 202

@app.route("/client-get", methods=["GET"])
def getFile():
    if not os.path.exists(CONTENT_FILE):
        abort(404, "No content available")
    with open(CONTENT_FILE, "r") as f:
        content = f.read()
    return jsonify({"content": content}), 200

@app.route("/server-get-file", methods=["GET"])
def ret():
    if not os.path.exists(REQUESTED_FILE):
        abort(404, "No file requested")
    with open(REQUESTED_FILE, "r") as f:
        o = f.read().strip()
    return jsonify({"file": o}), 200

@app.route("/server-send", methods=["POST"])
def upload():
    data = request.get_json(silent=True)
    if not data:
        abort(400, "JSON body required")
    # Accept legacy keys 'code', 'fileName', or 'content'
    content = data.get("content") or data.get("code") or data.get("fileName")
    if content is None:
        abort(400, "content required")
    if not isinstance(content, str):
        abort(400, "content must be a string")
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        abort(413, "content too large")
    # atomic write
    fd, tmp = tempfile.mkstemp()
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, CONTENT_FILE)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
    return jsonify({"status": "Success"}), 200

if __name__ == "__main__":
    # Only use debug mode in development
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
