#!/usr/bin/env python3
"""
tuya_enduser - CLI for Tuya's 2C "end-user" API using an OpenClaw-style
bearer key (sk-...). This is the path that works with a `TUYA_API_KEY`
without needing the IoT-project "Link App Account" QR step.

The region is auto-detected from the key prefix (the two chars after `sk-`):
  AY China      -> https://openapi.tuyacn.com
  AZ US West    -> https://openapi.tuyaus.com
  EU Cent.Europe-> https://openapi.tuyaeu.com
  IN India      -> https://openapi.tuyain.com
  UE US East    -> https://openapi-ueaz.tuyaus.com
  WE West.Europe-> https://openapi-weaz.tuyaeu.com
  SG Singapore  -> https://openapi-sg.iotbing.com

Auth: every request sends `Authorization: Bearer <api_key>`.

Config: TUYA_API_KEY env var, or "api_key" in tuya_config.json (gitignored).

Usage:
  ./tuya_enduser.py devices                     list all devices (+ ids)
  ./tuya_enduser.py detail  <device_id>         device detail + current properties
  ./tuya_enduser.py model   <device_id>         Thing Model (property codes)
  ./tuya_enduser.py control <device_id> '<json-properties>'
                                                issue properties, e.g. '{"switch_1":true}'

IR / RF blaster helpers (category wnykq, e.g. MOES UFO-R2-RF):
  ./tuya_enduser.py ir-learn      <device_id>   put blaster into learning mode
  ./tuya_enduser.py ir-learn-exit <device_id>   leave learning mode
  ./tuya_enduser.py ir-code       <device_id>   read last learned code (ir_study_code)
  ./tuya_enduser.py ir-send-raw   <device_id> '<json>'   write raw ir_send payload
"""
import json
import os
import sys
import urllib.request
import urllib.error

PREFIX_HOSTS = {
    "AY": "https://openapi.tuyacn.com",
    "AZ": "https://openapi.tuyaus.com",
    "EU": "https://openapi.tuyaeu.com",
    "IN": "https://openapi.tuyain.com",
    "UE": "https://openapi-ueaz.tuyaus.com",
    "WE": "https://openapi-weaz.tuyaeu.com",
    "SG": "https://openapi-sg.iotbing.com",
}


def load_key():
    key = os.environ.get("TUYA_API_KEY")
    if not key:
        path = os.environ.get("TUYA_CONFIG", "tuya_config.json")
        if os.path.exists(path):
            with open(path) as fh:
                key = json.load(fh).get("api_key")
    if not key:
        sys.exit("Missing API key: set TUYA_API_KEY or add \"api_key\" to tuya_config.json")
    if not key.startswith("sk-") or len(key) < 5:
        sys.exit("API key must look like sk-<PREFIX>...")
    prefix = key[3:5].upper()
    if prefix not in PREFIX_HOSTS:
        sys.exit(f"Unknown key region prefix {prefix!r}; expected one of {list(PREFIX_HOSTS)}")
    return key, PREFIX_HOSTS[prefix]


class EndUser:
    def __init__(self):
        self.key, self.host = load_key()

    def _req(self, method, path, body=""):
        headers = {"Authorization": "Bearer " + self.key,
                   "Content-Type": "application/json"}
        req = urllib.request.Request(
            self.host + path, method=method,
            data=body.encode() if body else None, headers=headers)
        try:
            resp = json.load(urllib.request.urlopen(req, timeout=30))
        except urllib.error.HTTPError as e:
            sys.exit(f"HTTP {e.code}: {e.read().decode()}")
        if not resp.get("success", False):
            sys.exit(f"Tuya API error {resp.get('code')}: {resp.get('msg')}")
        return resp["result"]

    def get(self, path):
        return self._req("GET", path)

    def post(self, path, obj):
        return self._req("POST", path, json.dumps(obj))


def pretty(o):
    print(json.dumps(o, indent=2, ensure_ascii=False))


def cmd_devices(a, args):
    r = a.get("/v1.0/end-user/devices/all")
    for d in r.get("devices", []):
        print(f"{d.get('device_id'):26}  {d.get('category'):8}  "
              f"{'online' if d.get('online') else 'offline':7}  "
              f"{d.get('category_name','')}  |  {d.get('name')}")


def cmd_detail(a, args):
    pretty(a.get(f"/v1.0/end-user/devices/{args[0]}/detail"))


def cmd_model(a, args):
    r = a.get(f"/v1.0/end-user/devices/{args[0]}/model")
    # model comes back as a JSON string; expand it for readability
    m = r.get("model")
    pretty(json.loads(m) if isinstance(m, str) else r)


def _issue(a, device_id, props):
    return a.post(f"/v1.0/end-user/devices/{device_id}/shadow/properties/issue",
                  {"properties": json.dumps(props)})


def cmd_control(a, args):
    pretty(_issue(a, args[0], json.loads(args[1])))


def cmd_ir_learn(a, args):
    pretty(_issue(a, args[0], {"ir_send": json.dumps({"control": "study"})}))


def cmd_ir_learn_exit(a, args):
    pretty(_issue(a, args[0], {"ir_send": json.dumps({"control": "study_exit"})}))


def cmd_ir_code(a, args):
    d = a.get(f"/v1.0/end-user/devices/{args[0]}/detail")
    code = d.get("properties", {}).get("ir_study_code")
    print(code if code else "(no learned code reported yet - run ir-learn, press a button, retry)")


def cmd_ir_send_raw(a, args):
    # args[1] is the JSON object to place inside ir_send, e.g.
    #   '{"control":"study_key","study_code":"<base64>"}'
    pretty(_issue(a, args[0], {"ir_send": args[1]}))


COMMANDS = {
    "devices": (cmd_devices, 0),
    "detail": (cmd_detail, 1),
    "model": (cmd_model, 1),
    "control": (cmd_control, 2),
    "ir-learn": (cmd_ir_learn, 1),
    "ir-learn-exit": (cmd_ir_learn_exit, 1),
    "ir-code": (cmd_ir_code, 1),
    "ir-send-raw": (cmd_ir_send_raw, 2),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 else 2)
    fn, need = COMMANDS[sys.argv[1]]
    args = sys.argv[2:]
    if len(args) < need:
        sys.exit(f"'{sys.argv[1]}' needs {need} argument(s).")
    fn(EndUser(), args)


if __name__ == "__main__":
    main()
