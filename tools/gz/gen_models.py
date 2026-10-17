#!/usr/bin/env python3
"""Generate emissive plane models (lid/open x 13 times) from one synthetic seed. Unique texture file per model."""
import shutil
import sys
from pathlib import Path

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 100
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
        fname = name + '.png'
        shutil.copy(img, tex / fname)
        (d / 'model.sdf').write_text(SDF.replace('TEXFILE', fname))
        n += 1
print('generated', n, 'models from', src)
