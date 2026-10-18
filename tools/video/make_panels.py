#!/usr/bin/env python3
"""Right-top (detector view + overlay) and right-bottom (status panel) images for the video.
Seed 112, recording v5. Detector settings unchanged (tools/eval/detect_track.py)."""
import copy
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/mnt/llm-storage/pai-final')
VID = ROOT / 'recordings' / 'video'
REC = os.environ.get('REC', 'v6')
SRC = VID / ('patrol6_' + REC)
OUT = VID / 'panels'
LOG = VID / ('patrol6_log_seed112_%s.jsonl' % REC)
NOTI = VID / ('notify_log_seed112_%s.jsonl' % REC)
REC0 = float((VID / ('rec_start_%s.txt' % REC)).read_text())
sys.path.insert(0, str(ROOT / 'tools' / 'eval'))
from detect_track import CFG, detect, merge_duplicates, update  # noqa: E402
sys.path.insert(0, str(ROOT / 'ros2_ws' / 'src' / 'dish_bringup' / 'scripts'))
from dish_vision import warp  # noqa: E402

PPM, R_DISH, PEND_OBS = 6.5, 43.5, 2
TS = list(range(0, 73, 6))
DAYS = ['Fri', 'Sat', 'Sun', 'Mon']
GREEN, YELLOW, RED, ORANGE = (40, 220, 60), (255, 210, 0), (255, 80, 70), (255, 160, 40)
WHITE, GRAY, BG = (240, 240, 240), (150, 150, 155), (24, 26, 30)
FONT = {True: '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        False: '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'}


def F(size, bold=False):
    p = FONT[bold]
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


def clock(t):
    h = 9 + t
    return '%s %02d:00' % (DAYS[h // 24], h % 24)


def researcher(t):
    if t >= 72:
        return 'IN LAB (Monday morning)', GREEN
    if t < 9:
        return 'IN LAB', GREEN
    return 'AWAY (left Fri 18:00)', ORANGE


rows = {r['t_h']: r for r in (json.loads(l) for l in open(LOG))}
notices = [json.loads(l) for l in open(NOTI)]
OUT.mkdir(parents=True, exist_ok=True)

# --- detector states per time (same procedure as the patrol) ---
ref = cv2.cvtColor(cv2.imread(str(SRC / 'warp' / 'lid_t000.png')), cv2.COLOR_BGR2GRAY)
tracks, states, ok = [], {}, 0
for t in TS:
    bgr = cv2.imread(str(SRC / 'warp' / ('lid_t%03d.png' % t)))
    update(tracks, detect(bgr[..., ::-1].copy(), PPM, R_DISH, CFG, ref), t, CFG)
    m = merge_duplicates(copy.deepcopy(tracks), CFG['merge_frac'])
    col = [tr for tr in m if tr['status'] == 'colony']
    pend = [tr for tr in m if tr['status'] == 'new' and len(tr['obs']) >= PEND_OBS]
    states[t] = (col, pend)
    same = (len(col), len(pend)) == (rows[t]['n_col'], rows[t]['n_pend'])
    ok += same
    print('t=%2dh confirmed %2d suspected %d | log %2d %d %s' % (
        t, len(col), len(pend), rows[t]['n_col'], rows[t]['n_pend'], 'OK' if same else 'DIFF'))
print('match with patrol log: %d / %d' % (ok, len(TS)))


# --- right-top: detector view with overlay (640x640) ---
def right_top(bgr, t, header, reflection=None):
    col, pend = states[t]
    im = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).convert('RGBA')
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for trs, c in ((pend, YELLOW), (col, GREEN)):
        for tr in trs:
            r = max(9.0, float(tr['obs'][-1][1]) * 1.3 + 5.0)
            d.ellipse([tr['x'] - r, tr['y'] - r, tr['x'] + r, tr['y'] + r], outline=c + (255,), width=3)
    if reflection is not None:
        ex, ey = reflection
        tx, ty = max(10, int(ex) - 230), min(560, int(ey) + 30)
        txt = 'ceiling-light reflection on lid'
        tw = d.textlength(txt, font=F(18))
        d.rectangle([tx - 6, ty - 4, tx + tw + 6, ty + 24], fill=(0, 0, 0, 150))
        d.text((tx, ty), txt, font=F(18), fill=WHITE + (255,))
        d.line([tx + tw * 0.75, ty - 4, ex, ey], fill=WHITE + (220,), width=2)
    d.rectangle([0, 0, 640, 66], fill=(0, 0, 0, 175))
    d.text((14, 6), header, font=F(26, True), fill=WHITE + (255,))
    d.text((14, 38), '%s    Confirmed: %d    Suspected: %d' % (clock(t), len(col), len(pend)),
           font=F(19), fill=WHITE + (255,))
    d.rectangle([0, 600, 640, 640], fill=(0, 0, 0, 160))
    d.ellipse([16, 610, 36, 630], outline=GREEN + (255,), width=3)
    d.text((44, 608), 'confirmed colony', font=F(18), fill=WHITE + (255,))
    d.ellipse([236, 610, 256, 630], outline=YELLOW + (255,), width=3)
    d.text((264, 608), 'suspected (seen, not yet growing)', font=F(18), fill=WHITE + (255,))
    return Image.alpha_composite(im, ov).convert('RGB')


def band_end():
    """Lower end of the static ceiling-light reflection bands, found in the t=0 lid image."""
    g = cv2.cvtColor(cv2.imread(str(SRC / 'warp' / 'lid_t000.png')), cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    inside = np.hypot(xx - (w - 1) / 2.0, yy - (h - 1) / 2.0) <= 40.0 * PPM
    med = float(np.median(g[inside]))
    m = ((g > med + 25) & inside).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 500]
    ys, xs = np.nonzero(np.isin(lab, keep))
    pts = np.stack([xs, ys], axis=1).astype(float)
    c = pts.mean(axis=0)
    ax = np.linalg.svd(pts - c, full_matrices=False)[2][0]
    proj = (pts - c) @ ax
    e1, e2 = c + ax * proj.min(), c + ax * proj.max()
    end = max((e1, e2), key=lambda e: e[1])
    print('reflection bands: %d components, agar median %.0f, ends (%.0f,%.0f) (%.0f,%.0f), label at lower end'
          % (len(keep), med, e1[0], e1[1], e2[0], e2[1]))
    return float(end[0]), float(end[1])


REFL = band_end()
for t in TS:
    right_top(cv2.imread(str(SRC / 'warp' / ('lid_t%03d.png' % t))), t,
              'View through lid', REFL).save(OUT / ('rt_lid_t%03d.png' % t))
opened = [t for t in TS if rows[t]['opened']]
for t in opened:
    right_top(warp(cv2.imread(str(SRC / ('open_t%03d.png' % t))), 'open'), t,
              'Lid OFF  (photo for the notification)').save(OUT / ('rt_open_t%03d.png' % t))
wait = Image.new('RGB', (640, 640), BG)
d = ImageDraw.Draw(wait)
d.text((40, 290), 'Fixed camera: waiting for the first image', font=F(24), fill=GRAY)
wait.save(OUT / 'rt_wait.png')


# --- right-bottom: status panel (640x440) ---
def panel(t, lid_open, n_open, total_open, show_conf):
    col, pend = states[t]
    im = Image.new('RGB', (640, 440), BG)
    d = ImageDraw.Draw(im)
    d.text((22, 14), clock(t), font=F(40, True), fill=WHITE)
    d.text((300, 22), 'culture time  t = %d h' % t, font=F(20), fill=WHITE)
    d.text((22, 66), 'Checked every 6 h through the closed lid', font=F(18), fill=GRAY)
    who, c = researcher(t)
    d.text((22, 104), 'Researcher:', font=F(22), fill=WHITE)
    d.text((160, 104), who, font=F(22, True), fill=c)
    if lid_open:
        d.text((22, 146), 'Lid:', font=F(22), fill=WHITE)
        d.text((80, 146), 'OPEN', font=F(22, True), fill=RED)
    else:
        d.text((22, 146), 'Lid:', font=F(22), fill=WHITE)
        d.text((80, 146), 'closed', font=F(22, True), fill=WHITE)
    d.text((230, 150), 'opened %d %s, total %.1f s' % (n_open, 'time' if n_open == 1 else 'times', total_open), font=F(18), fill=GRAY)
    d.text((22, 188), 'Colonies:', font=F(22), fill=WHITE)
    d.text((140, 188), 'confirmed %d' % len(col), font=F(22, True), fill=GREEN)
    d.text((320, 188), 'suspected %d' % len(pend), font=F(22, True), fill=YELLOW)
    d.text((22, 238), 'Notifications to researcher', font=F(20, True), fill=WHITE)
    y = 272
    for n in notices:
        if n['kind'] == 'suspected' and t >= n['t_h']:
            d.text((32, y), '%s  SUSPECTED' % clock(n['t_h']), font=F(20, True), fill=YELLOW)
            d.text((300, y + 2), 'photo through lid (not opened)', font=F(17), fill=WHITE)
            y += 36
        if n['kind'] == 'confirmed' and show_conf:
            d.text((32, y), '%s  CONFIRMED' % clock(n['t_h']), font=F(20, True), fill=GREEN)
            d.text((300, y + 2), 'photo with lid off', font=F(17), fill=WHITE)
            y += 36
    if y == 272:
        d.text((32, y), '(none yet)', font=F(18), fill=GRAY)
    d.text((22, 408), 'Simulation  |  synthetic dish images (seed 112)', font=F(15), fill=GRAY)
    return im


open_t = {t: rows[t]['open_time'] for t in opened}
conf_t = min(n['t_h'] for n in notices if n['kind'] == 'confirmed')


def n_tot(before_t, inclusive):
    ts = [x for x in opened if (x <= before_t if inclusive else x < before_t)]
    return len(ts), sum(open_t[x] for x in ts)


for t in TS:
    n, tot = n_tot(t, False)
    panel(t, False, n, tot, t > conf_t).save(OUT / ('p_t%03d.png' % t))
for t in opened:
    n, tot = n_tot(t, False)
    panel(t, True, n, tot, False).save(OUT / ('p_t%03d_open.png' % t))
    n, tot = n_tot(t, True)
    panel(t, False, n, tot, t >= conf_t).save(OUT / ('p_t%03d_after.png' % t))

# --- timeline for compositing (seconds in gazebo_raw_v5.mp4) ---
tl = [dict(at=0.0, rt='rt_wait.png', panel='p_t000.png')]
for t in TS:
    w = rows[t]['wall']
    tl.append(dict(at=round(w['lid_grab'] - REC0, 2), rt='rt_lid_t%03d.png' % t, panel='p_t%03d.png' % t, t_h=t))
    if rows[t]['opened']:
        tl.append(dict(at=round(w['attach'] - REC0, 2), rt='rt_lid_t%03d.png' % t, panel='p_t%03d_open.png' % t, t_h=t))
        tl.append(dict(at=round(w['open_grab'] - REC0, 2), rt='rt_open_t%03d.png' % t, panel='p_t%03d_open.png' % t, t_h=t))
        tl.append(dict(at=round(w['detach'] - REC0, 2), rt='rt_lid_t%03d.png' % t, panel='p_t%03d_after.png' % t, t_h=t))
(OUT / 'timeline.json').write_text(json.dumps(tl, indent=1))
print('timeline entries:', len(tl))
for e in tl:
    print('  %6.2f s  %-18s %s' % (e['at'], e['rt'], e['panel']))

# --- preview sheet ---
cols = []
for rt, p in (('rt_lid_t018.png', 'p_t018.png'), ('rt_open_t024.png', 'p_t024_after.png')):
    a = np.array(Image.open(OUT / rt))
    b = np.array(Image.open(OUT / p))
    cols.append(np.vstack([a, b]))
Image.fromarray(np.hstack(cols)).resize((960, 810)).save(VID / 'panels_preview.png')
print('files:', len(list(OUT.glob('*.png'))), '-> preview', VID / 'panels_preview.png')
