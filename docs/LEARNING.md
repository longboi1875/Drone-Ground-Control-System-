# SkyLink learning path

Use these tours after you have run `make dev`. Each section follows one value from its origin to the UI instead of asking you to read every file.

## 1. Follow a telemetry frame

Start at `DemoVehicle.telemetry()` in `mission_service/skylink/vehicle.py`. It yields a typed `TelemetrySnapshot`. `MissionService._stream_telemetry()` logs that object and publishes it. The `/ws/telemetry` route serializes the same object. In the browser, `useSkyLink()` receives it and `GroundStation` renders its fields.

Experiment: change `telemetry_hz` in `.env`, restart the service, and watch how smoothly heading and position update.

## 2. Follow an acknowledged command

`CommandControls` generates the user action. `lib/api.ts` attaches a UUID. `POST /api/commands` calls `MissionService.issue_command()`, which first inserts the command into SQLite. Only a newly inserted ID starts `_dispatch()`. The adapter executes once and the command becomes acknowledged or failed.

Experiment: send the same JSON command twice with curl. The first response has `created: true`; the second has `created: false`. Change the command type but keep the UUID to see the `409` conflict.

## 3. Follow a mission

Map clicks create typed `Waypoint` objects. `MissionPanel` can reorder, delete, export, save, and upload them. Pydantic validates coordinates, altitude, speed, and acceptance radius before SQLite or PX4 sees the mission. `MavsdkVehicle.upload_mission()` is the only location that translates SkyLink waypoints into MAVSDK objects.

Experiment: edit an exported mission to use an altitude above 120 m and upload it through the API. The validation error arrives before any vehicle call.

## 4. Understand replay

Every frame is stored with a flight ID. `ReplayController` loads frames in timestamp order and republishes them through the normal telemetry bus. It changes only `source` to `replay`. The UI therefore reuses its live rendering path while locking operations.

Experiment: compare 0.5x and 4x playback and confirm the route is unchanged while wall-clock playback time changes.

## 5. Break the link safely

`LinkProxy` owns two UDP sockets, one facing PX4 and one facing MAVSDK. `ImpairmentEngine` makes seeded drop, delay, and duplication decisions independently of socket code. This separation makes the failure logic easy to test without PX4.

Experiment: run `make benchmark`, change only the seed, and compare results. Then restore seed 481 and confirm the original output returns.

## Questions worth answering in an interview

- Why does the browser not connect to MAVLink directly?
- What guarantee does command deduplication provide, and what does it not provide?
- Why does replay use the same telemetry contract as the live vehicle?
- How would you move the deduplication boundary onto an onboard companion computer?
- Which benchmark metrics matter more than raw packet delivery rate for an operator?
