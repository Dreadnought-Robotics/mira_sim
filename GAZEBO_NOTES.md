To fix the sea floor orientation, change the <pose> in src/common_resources/data/object_files/tacc_seafloor/model.sdf

Need some kind of image enshittifier for the camera images

Main repo should be plug & play with this, ie: auto connect / auto detect sim.

ALT HOLD WORKS!

lots of small QoL fixes need to be made.

---

## 2026-08-27 progress

- Gazebo is now the primary/actively-maintained sim; Stonefish legacy path removed (2026-08-27: `stonefish.Dockerfile`, `src/vortex_simulator/`, `src/dnt_simulator/` deleted).
- `ardupilot_gazebo`, `bluerov2_gz`, `sauvc_sim` were force-inlined instead of
  real submodules (96cba4a). Fixed: they're now proper `git submodule`s
  pinned to the exact commits that were inlined (verified via `git ls-remote`
  before converting).
- `docker-compose.yml`'s `mira_sim` service was still pointing at the old
  `stonefish.Dockerfile`. Fixed: it now builds `src/bluerov2_gz/docker/Dockerfile`.
- GPU is now auto-detected at container start (`docker/gazebo-entrypoint.sh`):
  falls back to `LIBGL_ALWAYS_SOFTWARE=1` + `ogre` when no `/dev/dri`/nvidia
  GPU is present, uses `ogre2` hardware rendering otherwise. A real GPU can
  additionally be passed through explicitly with
  `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up mira_sim`.
- Stonefish depth-hold/laggy-movement root causes found and fixed on the
  legacy path before removal: `ardusim_patch.py` hardcoded `namespace='blueboat'` (bridge
  was subscribing to nonexistent topics, so PWM was never actually applied);
  `TACC_PIPELINE.scn` had `water density="1548.0"` (way over real seawater
  density, fighting the vehicle's buoyancy trim) - now 1031.0 in Gazebo worlds.
- Correction: there is no missing barometer sensor to add. ArduSub's SITL
  (`AP_Baro_SITL.cpp`) already synthesizes a noisy simulated barometer
  reading from `_sitl->state.altitude` - the ground-truth position Gazebo
  sends over the JSON FDM link - applying `SIM_BARO_DRIFT`/`SIM_BARO_RND`/etc
  before it reaches the EKF. This is standard for any JSON-backend physics
  engine, not something the sim side needs to provide. If more realistic
  noise is wanted, tune those `SIM_BARO_*` params in ArduSub, not the sim.
- `src/bluerov2_gz` submodule now points at a fork
  (github.com/davidnoronha1/bluerov2_gz, `upstream` remote still set to
  clydemcqueen/bluerov2_gz) in case local model changes are needed later; no
  changes have been made there yet.
