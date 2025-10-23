
from flask import Response, Flask, jsonify, request, abort, render_template_string, session
import os
import random

app = Flask(__name__)

#os.path.exists(filename)

secKey = os.getenv("SECRET")

@app.before_request
def check_auth():
    key = request.headers.get("X-Auth-Key")
    if key != secKey:
        abort(403)

@app.route("/addrs-add")
def add():
    o = open("onlineAddrs", "a")
    o.write(f'{request.remote_addr}\n')
    o.close()
    abort(200)

@app.route("/addrs-remove")
def remove():
    addrs = str(open("onlineAddrs", "r").read()).split("\n")
    incomingReqIp = str(request.remote_addr)
    addrs.remove(f'{request.remote_addr}\n')
    open("onlineAddrs", "w").write(str(addrs).replace("[", "").replace("]", "").replace(",", ""))
    abort(200)


@app.route("/clear-index")
def clear():
    x = open("onlineAddrs", "w")
    x.write("")
    x.close()
@app.route("/addrs")
def returnAddrs():
    addrs = str(open("onlineAddrs", "r").read()).split("\n")
    return jsonify(addrs), 200


@app.route("/client-request", methods = ["POST"])
def send():
    data = request.json
    if not data:
        abort(400)
    
    fileName = data.get('file')
    o = open("requestedFile.txt", "w")
    o.write(fileName)
    o.close()
    return jsonify("Request sent... Awaiting response"), 202

@app.route("/client-get", methods = ["GET"])
def getFile():
    o = open("fileContent.txt", "r").read()
    return jsonify(o), 200


@app.route("/server-get-file")
def ret():
    o = open("requestedFile.txt", "r").read()
    return jsonify(o), 206

@app.route("/server-send", methods = ["POST"])
def upload():
    data = request.json
    if not data:
        abort("data not received")
    
    open("fileContent.txt", "w").write(data.get('code'))
    return jsonify("Success"), 200

if __name__ == "__main__":
    app.run(debug=True)
