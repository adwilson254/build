# Rivian cloud golden fixtures

These JSON files mirror the **shape** of real Rivian GraphQL responses consumed
by `selfdrive/rivian/mqttd.py` (`get_rivian_data`) and `api.py`. They drive the
cloud-API unit tests without contacting Rivian's servers.

## Capturing/refreshing from a real vehicle

The structure here is hand-built to match the parser. To validate against *real*
data, capture live responses on the device (or via the API client) and **scrub
all secrets/PII** before committing:

1. On a machine logged into the Rivian API, dump the two calls the daemon makes:
   - `get_user_info()`  -> `rivian_user_info.json`
   - `get_vehicle_state(vehicle_id)` -> `rivian_vehicle_state.json`
2. Scrub before saving:
   - replace `currentUser.vehicles[].id` / VIN with placeholders
   - remove any access/session tokens, emails, names, exact home coordinates
   - round/aliased GPS is fine; do not commit a real driveway location
3. Drop the scrubbed files here. The tests assert on derived values (unit
   conversions, topic mapping), so realistic numbers keep them meaningful.

Never commit `rivian_token.json`, session tokens, or unredacted location data.
