"""Rebuild every art asset of Message Ship (Blender runs one at a time; ~6 minutes).
python art/build_all.py [ship] [creatures] [kraken] [env] [cast]      (no args = all)
Env var BLENDER overrides the Blender path."""
import os
import subprocess
import sys
import time

ART = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ART, "_raw")
BL = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def blender(script, *a):
    subprocess.run([BL, "-b", "--python", os.path.join(ART, "blender", script), "--", *a], check=True,
                   stdout=subprocess.DEVNULL)


def py(script, *a):
    subprocess.run([sys.executable, os.path.join(ART, script), *a], check=True)


stages = sys.argv[1:] or ["ship", "creatures", "kraken", "env", "cast"]
t0 = time.time()
if "ship" in stages:
    blender("ship.py", RAW, "hull", "mast", "sails", "stations", "props", "flags", "fx")
    py("fx_pil.py", RAW, "ship")
    py("pack_atlas.py", "ship", RAW)
if "creatures" in stages:
    blender("sea_creatures.py", RAW)
    py("fx_pil.py", RAW, "creatures")
    py("pack_atlas.py", "creatures", RAW)
    py("make_preview_creatures.py")
if "kraken" in stages:
    blender("kraken.py", RAW)
    py("pack_atlas.py", "kraken", RAW)
if "env" in stages:
    blender("env.py", RAW)
    py("env_pil.py", RAW)
    py("pack_atlas.py", "env", RAW)
if "cast" in stages:
    blender("ms_render.py", "portrait", "all", RAW)
    blender("ms_render.py", "sprite", "all", RAW)
    py("pack_cast.py", "portraits", RAW)
    py("pack_cast.py", "sprites", RAW)
    py("make_preview_cast.py")
if "ship" in stages or "env" in stages:
    py("make_preview_ship.py")
    py("make_preview_env.py")
print(f"done in {time.time() - t0:.0f}s")
