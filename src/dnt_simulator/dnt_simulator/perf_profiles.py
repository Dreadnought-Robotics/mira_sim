"""Perf profiles for Stonefish - matches Gazebo gpu auto-detect pattern."""
import os
import multiprocessing
import subprocess

# 4 profiles matching Gazebo's ogre/ogre2 auto-select
PROFILES = {
    "nogpu": {
        "simulation_rate": "60.0",
        "window_res_x": "640",
        "window_res_y": "480",
        "rendering_quality": "low",
        "description": "Software rendering (LIBGL_ALWAYS_SOFTWARE=1), no GPU",
    },
    "low": {
        "simulation_rate": "80.0",
        "window_res_x": "800",
        "window_res_y": "600",
        "rendering_quality": "low",
        "description": "Low-end / iGPU, minimal load",
    },
    "medium": {
        "simulation_rate": "100.0",
        "window_res_x": "960",
        "window_res_y": "600",
        "rendering_quality": "low",
        "description": "Balanced (default, matches Gazebo ogre2 medium)",
    },
    "high": {
        "simulation_rate": "200.0",
        "window_res_x": "1280",
        "window_res_y": "720",
        "rendering_quality": "high",
        "description": "High-end discrete GPU, full quality",
    },
}

def has_nvidia_gpu() -> bool:
    try:
        # nvidia-smi exists and reports at least one GPU
        result = subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=2)
        return result.returncode == 0 and b"GPU" in result.stdout
    except Exception:
        return False

def has_dri() -> bool:
    return os.path.exists("/dev/dri")

def detect_profile() -> str:
    """Auto-detect profile like Gazebo entrypoint does."""
    # Env override
    env = os.environ.get("STONEFISH_PROFILE") or os.environ.get("MIRA_PROFILE") or os.environ.get("PROFILE")
    if env and env in PROFILES:
        return env
    # GPU check
    gpu = has_nvidia_gpu() or has_dri()
    if not gpu:
        return "nogpu"
    # CPU / mem heuristics
    try:
        nproc = multiprocessing.cpu_count()
    except Exception:
        nproc = 4
    # mem in GB
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    mem_gb = kb / 1024 / 1024
                    break
            else:
                mem_gb = 16
    except Exception:
        mem_gb = 16

    if nproc <= 4 or mem_gb < 8:
        return "low"
    if nproc <= 8 or mem_gb < 16:
        return "medium"
    return "high"

def get_profile(name: str = None) -> dict:
    if name is None:
        name = detect_profile()
    if name not in PROFILES:
        name = "medium"
    return PROFILES[name]
