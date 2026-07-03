# tuya_ir

Tiny, dependency-free CLI to control a Tuya / MOES **IR-RF blaster**
(tested target: **MOES UFO-R2-RF** — 38kHz IR + 433/315MHz RF) through the
Tuya Cloud OpenAPI.

Pure Python standard library — no `pip install`, no crypto backend needed.

There are **two** CLIs for the two Tuya auth models:

| CLI | Auth | When to use |
|-----|------|-------------|
| `tuya_enduser.py` | `sk-` bearer key (OpenClaw / 2C end-user API) | **Recommended.** Works immediately with a `TUYA_API_KEY`, no QR account-link step. Region auto-detected from the key prefix. |
| `tuya_ir.py` | Access ID + Secret, HMAC-SHA256 signed | Classic IoT-project OpenAPI. Requires linking your app account (QR scan) to the Cloud project first. |

## This account's devices

Discovered via `tuya_enduser.py devices`:

| Device ID | Category | Name |
|-----------|----------|------|
| `bf266820b117e9b16fwtnm` | `wnykq` Universal Remote Control | **Sala router 433** — the MOES UFO-R2-RF (IR/RF blaster) |
| `bfd1ebfa4823185251zjbs` | `qt` | Garage Door |
| `bf6bcc8eaa4c4de28b1yrz` | `qt` | Garage Door1 |
| `bfae52b42cef863595af2n` | `qt` | One-way switch |
| `bf2f36pru5kxzppj` | `jtmspro` | DLOCK 2 |
| `bf3af3266ebd5401b07rc7` | `jtmspro` | SmartLock |

The UFO-R2 exposes two Thing-Model properties: `ir_send` (write: issue IR/RF
commands, enter/exit learning) and `ir_study_code` (read: last learned code).

## Setup

1. Create a Cloud project at <https://iot.tuya.com> (data center **Central Europe**
   for `eu` devices).
2. In the project: **Devices → Link App Account → Add App Account**, then scan
   the QR with your **Smart Life / Tuya** app so your devices become visible to
   the API.
3. Copy `tuya_config.example.json` to `tuya_config.json` and fill in your
   **Access ID** and **Access Secret** (or export `TUYA_ACCESS_ID` /
   `TUYA_ACCESS_KEY` / `TUYA_REGION`). `tuya_config.json` is gitignored.

## Usage — recommended (bearer key)

```sh
./tuya_enduser.py devices                     # list all devices + ids
./tuya_enduser.py detail  <device_id>         # detail + current property state
./tuya_enduser.py model   <device_id>         # Thing Model (property codes)
./tuya_enduser.py control <device_id> '{"switch_1":true}'   # issue properties

# IR/RF blaster (UFO-R2) helpers:
./tuya_enduser.py ir-learn      <device_id>   # enter learning mode
./tuya_enduser.py ir-code       <device_id>   # read the learned code after pressing a button
./tuya_enduser.py ir-learn-exit <device_id>   # leave learning mode
./tuya_enduser.py ir-send-raw   <device_id> '{"control":"study_key","study_code":"<b64>"}'
```

## Usage — classic (HMAC, needs account link)

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
