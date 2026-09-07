<img width="1228" height="866" alt="image" src="https://github.com/user-attachments/assets/3ae59602-d557-415d-a915-ce183217f785" />

# Mira Simulator

Please see the [wiki](https://github.com/Dreadnought-Robotics/mira_sim/wiki) for installation & usage instructions.

## Running with Docker

Containers are built and pushed to GHCR automatically by [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml). `docker-compose.yml` is set up to pull those images by default and fall back to a local build if they aren't available:

```bash
# Try to pull the pre-built images from GHCR; falls back to a local build if unavailable/private
docker-compose pull || docker-compose build

# Start the stonefish simulator (GUI, needs an X server)
docker-compose run --rm mira_sim

# In a separate terminal, start the ArduPilot SITL
docker-compose run --rm ardupilot-sitl
```
