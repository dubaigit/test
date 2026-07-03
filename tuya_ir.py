#!/usr/bin/env python3
"""
tuya_ir - a tiny CLI to control a Tuya/MOES IR-RF blaster (e.g. MOES UFO-R2-RF)
through the Tuya Cloud OpenAPI.

Pure standard library: no third-party deps, no cffi/crypto backend needed.
Signing is HMAC-SHA256 exactly as required by the Tuya OpenAPI.

Config: reads credentials from (in order) environment variables or a JSON file
(default ./tuya_config.json). Never commit that file.

  TUYA_REGION      one of: eu, us, cn, in            (default: eu)
  TUYA_ACCESS_ID   Access ID / Client ID
  TUYA_ACCESS_KEY  Access Secret / Client Secret

Usage:
  ./tuya_ir.py devices                         list all linked devices (find your blaster's id)
  ./tuya_ir.py remotes  <ir_id>                list the sub-remotes learned on a blaster
  ./tuya_ir.py keys     <ir_id> <remote_id>    list the buttons on a remote
  ./tuya_ir.py send     <ir_id> <remote_id> <key>   fire a button (e.g. power)
  ./tuya_ir.py status   <device_id>            raw device status
  ./tuya_ir.py raw GET|POST <api_path> [json_body]  escape hatch for any endpoint

<ir_id> is the device id of the blaster itself (from `devices`).
"""
import hmac
import hashlib
import time
import json
import os
import sys
import urllib.request
import urllib.error

REGION_HOSTS = {
    "eu": "https://openapi.tuyaeu.com",
    "us": "https://openapi.tuyaus.com",
    "cn": "https://openapi.tuyacn.com",
    "in": "https://openapi.tuyain.com",
}
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def load_config():
    cfg = {
        "region": os.environ.get("TUYA_REGION"),
        "access_id": os.environ.get("TUYA_ACCESS_ID"),
        "access_key": os.environ.get("TUYA_ACCESS_KEY"),
    }
    path = os.environ.get("TUYA_CONFIG", "tuya_config.json")
    if os.path.exists(path):
        with open(path) as fh:
            file_cfg = json.load(fh)
        for k in ("region", "access_id", "access_key"):
            if not cfg[k]:
                cfg[k] = file_cfg.get(k)
    cfg["region"] = cfg["region"] or "eu"
    if not cfg["access_id"] or not cfg["access_key"]:
        sys.exit("Missing credentials: set TUYA_ACCESS_ID / TUYA_ACCESS_KEY "
                 "or create tuya_config.json (see tuya_config.example.json).")
    if cfg["region"] not in REGION_HOSTS:
        sys.exit(f"Unknown region {cfg['region']!r}; pick one of {list(REGION_HOSTS)}")
    return cfg


class Tuya:
    def __init__(self, cfg):
        self.host = REGION_HOSTS[cfg["region"]]
        self.cid = cfg["access_id"]
        self.secret = cfg["access_key"]
        self._token = None

    def _sign(self, method, path, token, body):
        t = str(int(time.time() * 1000))
        content_sha = hashlib.sha256(body.encode()).hexdigest() if body else EMPTY_SHA256
        string_to_sign = f"{method}\n{content_sha}\n\n{path}"
        msg = self.cid + (token or "") + t + string_to_sign
        sign = hmac.new(self.secret.encode(), msg.encode(), hashlib.sha256).hexdigest().upper()
        headers = {
            "client_id": self.cid,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json",
        }
        if token:
            headers["access_token"] = token
        return headers

    def _request(self, method, path, token="", body=""):
        headers = self._sign(method, path, token, body)
        req = urllib.request.Request(
            self.host + path, method=method,
            data=body.encode() if body else None, headers=headers)
        try:
            resp = json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            sys.exit(f"HTTP {e.code}: {e.read().decode()}")
        if not resp.get("success", False):
            sys.exit(f"Tuya API error {resp.get('code')}: {resp.get('msg')}")
        return resp

    def token(self):
        if not self._token:
            r = self._request("GET", "/v1.0/token?grant_type=1")
            self._token = r["result"]["access_token"]
        return self._token

    def get(self, path):
        return self._request("GET", path, self.token())

    def post(self, path, body_obj):
        return self._request("POST", path, self.token(), json.dumps(body_obj))


def pretty(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_devices(t, args):
    r = t.get("/v1.0/iot-01/associated-users/devices?size=100")
    devs = r["result"].get("devices", [])
    if not devs:
        print("No devices linked to this Cloud project yet.")
        print("On iot.tuya.com: Devices -> Link App Account -> scan the QR "
              "with your Smart Life app, then rerun.")
        return
    for d in devs:
        print(f"{d.get('id'):24}  {d.get('category'):10}  "
              f"{'online' if d.get('online') else 'offline':7}  {d.get('name')}")


def cmd_remotes(t, args):
    ir_id = args[0]
    pretty(t.get(f"/v2.0/infrareds/{ir_id}/remotes")["result"])


def cmd_keys(t, args):
    ir_id, remote_id = args[0], args[1]
    pretty(t.get(f"/v2.0/infrareds/{ir_id}/remotes/{remote_id}/keys")["result"])


def cmd_send(t, args):
    ir_id, remote_id, key = args[0], args[1], args[2]
    r = t.post(f"/v2.0/infrareds/{ir_id}/remotes/{remote_id}/command",
               {"key": key})
    print("sent" if r.get("success") else "failed:", key)
    pretty(r)


def cmd_status(t, args):
    pretty(t.get(f"/v1.0/devices/{args[0]}/status")["result"])


def cmd_raw(t, args):
    method, path = args[0].upper(), args[1]
    body = args[2] if len(args) > 2 else ""
    if method == "GET":
        pretty(t.get(path))
    else:
        pretty(t.post(path, json.loads(body) if body else {}))


COMMANDS = {
    "devices": (cmd_devices, 0),
    "remotes": (cmd_remotes, 1),
    "keys": (cmd_keys, 2),
    "send": (cmd_send, 3),
    "status": (cmd_status, 1),
    "raw": (cmd_raw, 2),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 2)
    name = sys.argv[1]
    args = sys.argv[2:]
    fn, need = COMMANDS[name]
    if len(args) < need:
        sys.exit(f"'{name}' needs {need} argument(s); see --help / no-args usage.")
    fn(Tuya(load_config()), args)


if __name__ == "__main__":
    main()
