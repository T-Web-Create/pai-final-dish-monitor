#!/usr/bin/env python3
"""Generate emissive plane models (lid/open x 13 times) from one synthetic seed. Unique texture file per model."""
import shutil
import sys
from pathlib import Path

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 100
bg = tuple(int(v) for v in sys.argv[2].split(',')) if len(sys.argv) > 2 else None
tag = sys.argv[3] if len(sys.argv) > 3 else ''
root = Path('/mnt/llm-storage/pai-final')
src = root / 'data' / 'synth' / ('seed_%04d' % seed)
dst = root / 'ros2_ws' / 'src' / 'dish_description' / 'models'

SDF = '''<?xml version="1.0"?>
<sdf version="1.9">
  <model name="dish_img">
    <static>true</static>
    <link name="link">
      <visual name="vis">
        <cast_shadows>false</cast_shadows>
        <geometry><plane><normal>0 0 1</normal><size>0.09846 0.09846</size></plane></geometry>
        <material>
          <diffuse>0 0 0 1</diffuse>
          <specular>0 0 0 1</specular>
          <pbr><metal>
            <emissive_map>materials/textures/TEXFILE</emissive_map>
            <metalness>0.0</metalness>
            <roughness>1.0</roughness>
          </metal></pbr>
        </material>
      </visual>
    </link>
  </model>
</sdf>
'''
def write_tex(src, dst, bg, ppm=6.5, r0=46.0, r1=46.75):
    """Copy the texture; if bg (B,G,R) is given, blend the area outside r0..r1 mm into bg."""
    if bg is None:
        shutil.copy(src, dst)
        return
    import cv2
    import numpy as np
    im = cv2.imread(str(src)).astype(np.float32)
    h, w = im.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - (w - 1) / 2.0, yy - (h - 1) / 2.0) / ppm
    a = np.clip((r - r0) / (r1 - r0), 0.0, 1.0)[..., None]
    out = im * (1.0 - a) + np.array(bg, np.float32) * a
    cv2.imwrite(str(dst), np.clip(out + 0.5, 0, 255).astype(np.uint8))


n = 0
for cond in ('lid', 'open'):
    for t in range(0, 73, 6):
        img = src / cond / ('t_%03d.png' % t)
        assert img.exists(), img
        name = 'img_%s_t%03d' % (cond, t)
        d = dst / name
        tex = d / 'materials' / 'textures'
        tex.mkdir(parents=True, exist_ok=True)
        for old in tex.glob('*.png'):
            old.unlink()
        fname = 's%d%s_' % (seed, tag) + name + '.png'
        write_tex(img, tex / fname, bg)
        (d / 'model.sdf').write_text(SDF.replace('TEXFILE', fname))
        n += 1
print('generated', n, 'models from', src)
