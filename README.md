# tuya_ir

Tiny, dependency-free CLI to control a Tuya / MOES **IR-RF blaster**
(tested target: **MOES UFO-R2-RF** — 38kHz IR + 433/315MHz RF) through the
Tuya Cloud OpenAPI.

Pure Python standard library — no `pip install`, no crypto backend needed.
Requests are signed with HMAC-SHA256 as the Tuya OpenAPI requires.

## Setup

1. Create a Cloud project at <https://iot.tuya.com> (data center **Central Europe**
   for `eu` devices).
2. In the project: **Devices → Link App Account → Add App Account**, then scan
   the QR with your **Smart Life / Tuya** app so your devices become visible to
   the API.
3. Copy `tuya_config.example.json` to `tuya_config.json` and fill in your
   **Access ID** and **Access Secret** (or export `TUYA_ACCESS_ID` /
   `TUYA_ACCESS_KEY` / `TUYA_REGION`). `tuya_config.json` is gitignored.

## Usage

```sh
./tuya_ir.py devices                          # list linked devices, find the blaster id
./tuya_ir.py remotes <ir_id>                  # list learned sub-remotes on the blaster
./tuya_ir.py keys    <ir_id> <remote_id>      # list buttons on a remote
./tuya_ir.py send    <ir_id> <remote_id> <key>  # fire a button, e.g. power / DIY_1
./tuya_ir.py status  <device_id>              # raw device status
./tuya_ir.py raw GET /v2.0/infrareds/<ir_id>/remotes   # call any endpoint
```

`<ir_id>` is the device id of the blaster itself (from `devices`).

## Notes

- IR/RF hubs like the UFO-R2 are controlled through the **cloud** IR API
  (`/v2.0/infrareds/...`); learned codes live in Tuya's cloud, not on the LAN.
- Region hosts: `eu` → openapi.tuyaeu.com, `us` → openapi.tuyaus.com,
  `cn` → openapi.tuyacn.com, `in` → openapi.tuyain.com.
