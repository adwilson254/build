# Replay route data for Rivian feature validation

Tests in `test_scorerd_replay.py` (and future CAN/car-port replay tests) run
**real recorded vehicle data** through the same logic the device uses. They
auto-skip when no route is present, so the fast gate is never blocked.

## Expected layout

Drop one or more openpilot route segments here:

```
tests/antigravity/routes/
  <route_name>--0/
    rlog.bz2          # or rlog.zst / rlog
    qcamera.ts        # optional, not needed for scorerd
```

A route is a recorded drive; a segment is ~1 minute of it. `scorerd` only needs
`carState`, `accelerometer`, and `modelV2` from `rlog`, so the camera files are
optional for these tests.

## Capturing a route from the comma (192.168.2.232)

Segments are stored on-device under `/data/media/0/realdata/`. To pull one:

```sh
# list recent segments on the device
ssh comma@192.168.2.232 'ls -t /data/media/0/realdata | head'

# copy a single segment locally (replace with a real segment dir name)
scp -r comma@192.168.2.232:/data/media/0/realdata/<SEGMENT_DIR> \
    tests/antigravity/routes/
```

Pick a segment with the car actually driving (engaged) so the smoothness and
path-accuracy metrics are meaningful.

## Privacy

Route logs can contain GPS traces and other sensitive telemetry. Do **not**
commit raw routes from your home/driveway to a public repo. Prefer keeping route
data local (this directory is gitignored) or use a sanitized/short segment.
