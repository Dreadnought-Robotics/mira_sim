# Troubleshooting Guide

## X11 Display & GUI Issues

### Symptom: Gazebo window doesn't appear

**Check 1: DISPLAY is not set**
```bash
echo $DISPLAY
```
If empty, you're likely connecting via SSH without X11 forwarding.

**Fix:**
```bash
ssh -X user@host  # Enable X11 forwarding
# Then retry
make simulator-gz
```

**Check 2: xauth cookie missing**
```bash
xauth list $DISPLAY
```
If no output, the auth cookie doesn't exist.

**Fix:**
```bash
make check-x11  # Auto-generates xauth cookie
# Or manually:
touch /tmp/.docker.xauth
xauth add $DISPLAY MIT-MAGIC-COOKIE-1 $(openssl rand -hex 16)
```

**Check 3: Using Wayland instead of X11**

Gazebo rendering is unstable on Wayland. Switch to X11:
1. Log out
2. In login manager (GNOME), select gear icon → **"GNOME on Xorg"**
3. Log back in
4. Verify: `echo $DISPLAY` should show `:0` or `:1`

**Check 4: Hostname resolution**
```bash
hostname -I  # Get your IP
# If SSH from another machine, ensure X server accepts TCP:
xhost +  # Allow any host (use with caution)
# Or specifically:
xhost +192.168.1.100  # Allow specific host
```

---

## QGroundControl Connection Issues

### Symptom: QGC shows "Waiting for heartbeat" or won't connect

**Check 1: Is SITL actually listening?**
```bash
docker compose logs ardupilot-sitl | tail -20
```

Look for:
```
Entering SITL mode
Ready to fly
```

If not present, SITL may be crashing. Check the full log for errors.

**Check 2: Is the port open?**
```bash
netstat -an | grep 14550
# or
ss -an | grep 14550
```

Should show:
```
LISTEN  127.0.0.1:14550   (UDP)
```

If it shows only IPv6 (`[::]` instead of `127.0.0.1`), check SITL's `-out` parameter in `docker-compose.yml`.

**Check 3: Firewall blocking UDP**
```bash
sudo ufw status
```

If active, allow the port:
```bash
sudo ufw allow 14550/udp
sudo ufw allow 14555/udp
```

**Check 4: SITL crashed silently**

Restart SITL and watch the output:
```bash
docker compose down ardupilot-sitl
docker compose up ardupilot-sitl  # Don't detach; watch the output
```

Watch for errors in the first few seconds.

**Check 5: QGC not set to the right port**

In QGC:
1. **Application Settings** → **Comm Links**
2. Select the connection in the list
3. Verify the port is **14550**
4. Host should be **127.0.0.1** (or your machine's IP if QGC is remote)
5. **Disconnect** any existing link before adding a new one

---

## Gazebo Performance Issues

### Symptom: Simulation stutters or runs slowly

**Check 1: CPU load**
```bash
# While simulator is running:
top -p $(docker inspect --format='{{.State.Pid}}' mira_sim)
```

ArduPilot + Gazebo can use 8-10 CPU cores under load. If you have fewer cores, performance will degrade.

**Check 2: Are you using software rendering?**
```bash
docker compose logs mira_sim | grep -i "render\|gpu\|llvm\|ogre"
```

If you see:
- `LIBGL_ALWAYS_SOFTWARE=1` — Software rendering (slower)
- `ogre2` — Hardware rendering (faster)

**Fix: Enable GPU**
```bash
MIRA_GPU=1 make simulator-gz
```

Requires NVIDIA GPU + NVIDIA Container Toolkit.

**Check 3: Gazebo GUI render settings**

Inside Gazebo:
1. **File** → **Graphics**
2. Reduce **Shadow Quality** (None, Low, Medium)
3. Disable **Shadows** entirely if CPU-bound
4. Close unnecessary camera windows

**Check 4: Network lag in MAVLink**

If the issue is vehicle response lag (not rendering):
```bash
# Check network latency between SITL and Gazebo
docker compose logs ardupilot-sitl | grep "JSON bridge\|FPS\|Hz"
```

Should see 400Hz or higher. If lower:
- Close browser/media apps consuming CPU
- Increase CPU allocation in `docker-compose.yml` (`cpus: 6` → `cpus: 8`)

**Check 5: Disk I/O bottleneck**

```bash
iotop -o  # Install with: apt install iotop
```

If I/O is high (>50% util), you may be CPU or memory constrained. Restart containers:
```bash
docker compose restart
```

---

## Docker Image & Build Issues

### Symptom: `docker pull` fails

**Error:** `net/http: request canceled`

**Fix: Rebuild locally instead**
```bash
docker compose build  # Rebuilds from Dockerfile (no pull)
docker compose up --no-recreate -d
```

First build takes 30-45 minutes (ArduPilot compilation).

### Symptom: Out of disk space

```bash
docker system df  # Show disk usage
docker image prune -a  # Remove unused images
docker builder prune  # Clear build cache
```

If still full:
```bash
du -sh ~/.docker/
# Relocate Docker data (if on small root partition):
# https://docs.docker.com/engine/daemon/
```

### Symptom: Container crashes on start

```bash
docker compose logs mira_sim
docker compose logs ardupilot-sitl
```

Common errors:
- `mount: /workspace: permission denied` — Check volume mount permissions in `docker-compose.yml`
- `NVIDIA runtime not available` — Install NVIDIA Container Toolkit or use `MIRA_GPU=0`
- `OOM (out of memory)` — Increase RAM or reduce `cpus` in compose file

---

## Submodule & Git Issues

### Symptom: Submodules not initialized

```bash
ls -la src/bluerov2_gz/  # Should have files, not be empty
```

If empty:
```bash
git submodule update --init --recursive
```

### Symptom: Submodule changes not reflected in container

Rebuild the image:
```bash
docker compose build --no-cache  # Force full rebuild
docker compose up --build --no-recreate -d
```

### Symptom: Merge conflicts in `.gitmodules`

```bash
git status
# Should show conflicts in `.gitmodules` only
git checkout --theirs .gitmodules
git add .gitmodules
git commit -m "Resolve submodule conflicts"
```

---

## Environment Variable Issues

### Symptom: DISPLAY not passed to container

```bash
docker compose exec mira_sim printenv DISPLAY
```

If empty or wrong:
```bash
DISPLAY=:0 docker compose up --no-recreate -d mira_sim
# Or export it in your shell:
export DISPLAY=:0
make simulator-gz
```

### Symptom: GPU not auto-detected

```bash
# Check if nvidia-smi works on host
nvidia-smi

# Check which service was selected
docker compose logs mira_sim | head -5
```

If using `mira_sim` but you have a GPU:
```bash
MIRA_GPU=1 make simulator-gz
```

---

## Makefile Issues

### Symptom: `make` commands fail with permission errors

```bash
ls -la Makefile
# Should be readable by your user (644 or 755)

chmod +x docker/gazebo-entrypoint.sh
chmod +x docker/x11-setup.sh
chmod +x Makefile
```

### Symptom: Virtual environment activation fails

```bash
which python3
python3 --version

# Ensure you don't have an active venv:
deactivate 2>/dev/null
echo $VIRTUAL_ENV  # Should be empty
```

### Symptom: `rosdep` not found (for host ROS builds)

Only needed if building ROS packages on the host. For Docker-only simulation, you can skip this.

```bash
sudo apt install python3-rosdep
rosdep update
```

---

## Sensor & Data Issues

### Symptom: No camera images in Gazebo

1. Check if cameras are spawned in the world file (`.world`):
   ```bash
   grep -i "camera\|sensor" worlds/tacc.world
   ```

2. Verify plugin paths in `docker-compose.yml`:
   ```bash
   GZ_SIM_RESOURCE_PATH  # Should include worlds, models, sauvc_sim
   ```

3. Restart Gazebo:
   ```bash
   docker compose exec mira_sim gz sim bluerov2_heavy_underwater.world
   ```

### Symptom: Barometer/depth readings nonsensical

See [GAZEBO_NOTES.md](../GAZEBO_NOTES.md) for detailed explanation. The issue was fixed by:
- Setting correct `home location` in ArduPilot SITL
- Using correct `water density` (1031.0, not 1548.0)
- Pinning `FRAME_CONFIG=2` for 6DOF mixing

No changes needed on your end—the fix is baked into the current containers.

---

## Networking Issues

### Symptom: Can't connect to simulator from another machine

By default, SITL only listens on `127.0.0.1:14550` (localhost). To allow remote connections:

Edit `docker-compose.yml`, change:
```yaml
--out=udp:0.0.0.0:14550  # All interfaces, from localhost only
--out=udp:0.0.0.0:14550  # Already does this (check line 54)
```

Then connect QGC from another host using your machine's IP:
```
Connection → Port: 14550, Host: 192.168.x.y
```

### Symptom: High latency / packet loss

```bash
# Check container network:
docker inspect mira_sim | grep -A 5 '"Networks"'

# Monitor traffic:
docker stats  # See CPU, memory, network I/O
```

If network I/O is saturated, reduce rendering or use `network_mode: host` (already enabled in compose).

---

## Still Stuck?

1. **Check logs:**
   ```bash
   docker compose logs -f  # Follow all services
   ```

2. **Inspect containers:**
   ```bash
   docker compose ps  # Status
   docker inspect mira_sim  # Full config
   ```

3. **Rebuild from scratch:**
   ```bash
   docker compose down -v  # Remove volumes too
   docker system prune -a   # Clean all images
   git submodule update --init --recursive
   docker compose build
   docker compose up --no-recreate -d
   ```

4. **Check [GAZEBO_NOTES.md](../GAZEBO_NOTES.md)** for integration details and known issues.
