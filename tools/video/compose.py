#!/usr/bin/env python3
"""Compose the video: Gazebo (left), detector view (right-top), status panel (right-bottom),
narration with word-by-word highlighted captions, and text cards. Seed 112, recording v5.
Usage: uv run python compose.py [--until SECONDS] [--out NAME]"""
import argparse
import json
import subprocess
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

VID = Path('/mnt/llm-storage/pai-final/recordings/video')
RAW = VID / 'gazebo_raw_v6.mp4'
PAN = VID / 'panels'
NAR = VID / 'narr'
OUTD = VID / 'out'
W, H, FPS, SR = 1920, 1080, 30, 24000
BG = (24, 26, 30)
WHITE, GRAY, CYAN = (240, 240, 240), (110, 112, 118), (90, 200, 255)
GREEN, YELLOW, ORANGE, RED = (40, 220, 60), (255, 210, 0), (255, 160, 40), (255, 80, 70)
GZ_W, GZ_H, GZ_Y = 1280, 1016, 32
CAM_RAW = (895, 372)
WIPE = 0.4
FONTP = {True: '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
         False: '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'}
_fc = {}


def F(size, bold=False):
    k = (size, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONTP[bold], size)
    return _fc[k]


def narr(i):
    return json.loads((NAR / (i + '.json')).read_text())


EDL = [
    dict(kind='card', card='intro', narr='intro', at=0.6, tail=0.5),
    dict(kind='video', src=(9.0, 28.8), speed=1, caps=[('s0_fri0900', 10.0)], camera=(0.5, 9.0)),
    dict(kind='video', src=(28.8, 46.3), speed=1, caps=[('s1_fri_pm', 35.4)]),
    dict(kind='video', src=(46.3, 82.7), speed=1, caps=[('s2_sat0300', 52.6), ('s3_sat0900', 60.9)],
         hold=(53.1, 2.0)),
    dict(kind='video', src=(82.7, 170.5), speed=5, caps=[('s4_weekend', 89.3)]),
    dict(kind='card', card='monday', narr='monday', at=0.6, tail=0.5),
    dict(kind='card', card='summary', narr='summary', at=0.6, tail=1.2),
]


def s2o(seg, s):
    s0 = seg['src'][0]
    o = (s - s0) / seg['speed']
    if 'hold' in seg and s > seg['hold'][0]:
        o += seg['hold'][1]
    return o


def o2s(seg, u):
    s0, sp = seg['src'][0], seg['speed']
    if 'hold' in seg:
        hs, hd = seg['hold']
        uh = (hs - s0) / sp
        if u >= uh:
            return hs if u < uh + hd else s0 + (u - hd) * sp
    return s0 + u * sp


def in_hold(seg, u):
    if 'hold' not in seg:
        return False
    hs, hd = seg['hold']
    uh = (hs - seg['src'][0]) / seg['speed']
    return uh <= u < uh + hd


# ---------- text layout ----------
_dummy = ImageDraw.Draw(Image.new('RGB', (10, 10)))


def layout(words, font, x0, y0, max_w, line_h):
    out, x, y = [], x0, y0
    sp = _dummy.textlength(' ', font=font)
    for i, w in enumerate(words):
        t = w['text']
        tw = _dummy.textlength(t, font=font)
        if x > x0 and x + tw > x0 + max_w and t not in '.,:;!?':
            x, y = x0, y + line_h
        out.append((x, y, t, font, w))
        brk = i + 1 < len(words) and words[i + 1]['line'] != w['line']
        x += tw + (sp if (w.get('ws', True) or brk) else 0)
    return out, y + line_h


def wcol(w, now):
    st, en = w.get('start'), w.get('end')
    if st is None:
        return WHITE
    if now < st:
        return GRAY
    if now < en:
        return CYAN
    return WHITE


def draw_words(d, items, now, dy=0):
    for x, y, t, font, w in items:
        d.text((x, y + dy), t, font=font, fill=wcol(w, now))


# ---------- cards ----------
def tx(t):
    return 160 + t / 72.0 * 1600


def build_card(name, nd):
    bg = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(bg, 'RGBA')
    by = {}
    for w in nd['words']:
        by.setdefault(w['line'], []).append(w)
    items = []
    if name == 'intro':
        d.rectangle([120, 180, 128, 900], fill=GREEN)
        y = 190
        for li in sorted(by):
            if li == 0:
                font, mw, lh, x0 = F(72, True), 1000, 90, 170
            elif li == 1:
                font, mw, lh, x0 = F(34), 1000, 48, 170
            else:
                font, mw, lh, x0 = F(34), 960, 48, 190
                d.text((158, y), '\u2022', font=F(34), fill=GRAY)
            lay, y = layout(by[li], font, x0, y, mw, lh)
            items += lay
            y += 50 if li <= 1 else 22
        im = Image.open(PAN / 'rt_lid_t072.png').crop((0, 66, 640, 600)).resize((600, 500))
        bg.paste(im, (1220, 290))
        d.text((1220, 800), 'Simulated dish at Monday 9 a.m. (10 colonies)', font=F(22), fill=GRAY)
    elif name == 'monday':
        d.text((160, 130), 'Friday 9 a.m.  \u2192  Monday 9 a.m.', font=F(44, True), fill=WHITE)
        d.rectangle([tx(9), 360, tx(72), 470], fill=ORANGE + (45,))
        d.text((tx(9) + 10, 322), 'Researcher away (Friday 6 p.m. to Monday 9 a.m.)', font=F(24), fill=ORANGE)
        d.line([tx(0), 415, tx(72), 415], fill=GRAY, width=4)
        for t in range(0, 73, 6):
            d.ellipse([tx(t) - 5, 410, tx(t) + 5, 420], fill=WHITE)
        for t, lab in ((0, 'Fri 9 a.m.'), (15, 'Sat'), (39, 'Sun'), (63, 'Mon'), (72, 'Mon 9 a.m.')):
            d.line([tx(t), 470, tx(t), 490], fill=GRAY, width=2)
            d.text((tx(t) - 40, 495), lab, font=F(22), fill=GRAY)
        for t in (0, 24):
            d.polygon([(tx(t), 385), (tx(t) - 10, 365), (tx(t) + 10, 365)], fill=RED)
        d.ellipse([tx(18) - 14, 401, tx(18) + 14, 429], outline=YELLOW, width=5)
        d.ellipse([tx(24) - 14, 401, tx(24) + 14, 429], outline=GREEN, width=5)
        d.text((tx(18) - 20, 540), 'Sat 3 a.m.  SUSPECTED (lid closed)', font=F(24, True), fill=YELLOW)
        d.text((tx(24) - 20, 578), 'Sat 9 a.m.  CONFIRMED (lid opened)', font=F(24, True), fill=GREEN)
        d.polygon([(1500, 560), (1490, 540), (1510, 540)], fill=RED)
        d.text((1520, 540), 'lid opened', font=F(22), fill=GRAY)
        d.ellipse([1495, 580, 1505, 590], fill=WHITE)
        d.text((1520, 572), 'check (every 6 h)', font=F(22), fill=GRAY)
        y = 680
        for li in sorted(by):
            lay, y = layout(by[li], F(38), 160, y, 1600, 54)
            items += lay
            y += 10
    elif name == 'summary':
        d.text((150, 100), 'Results (simulation)', font=F(48, True), fill=WHITE)
        tiles = [('2 openings', GREEN, ['17.5 s in 72 h', 'vs 13 openings, ~116 s', 'if opened at every check']),
                 ('5 h', GREEN, ['median time from a colony', 'appearing to the first notice', '(30 held-out dishes)']),
                 ('0 / 30', GREEN, ['false alarms on', 'colony-free dishes', '(synthetic)'])]
        for k, (big, c, small) in enumerate(tiles):
            x = 150 + k * 570
            d.rounded_rectangle([x, 190, x + 520, 500], radius=18, fill=(36, 39, 45))
            d.text((x + 30, 215), big, font=F(72, True), fill=c)
            for j, s in enumerate(small):
                d.text((x + 30, 330 + j * 40), s, font=F(26), fill=WHITE if j == 0 else GRAY)
        y = 560
        for li in sorted(by):
            lay, y = layout(by[li], F(32), 150, y, 1620, 44)
            items += lay
            y += 12
    return bg, items


def card_frame(cache, seg, u, dur):
    bg, items = cache
    img = bg.copy()
    d = ImageDraw.Draw(img)
    draw_words(d, items, u - seg['at'])
    a = min(1.0, u / 0.3, (dur - u) / 0.3)
    arr = np.asarray(img).astype(np.float32)
    if a < 1.0:
        arr = arr * max(a, 0.0) + np.array(BG, np.float32) * (1 - max(a, 0.0))
    return arr.astype(np.uint8)


# ---------- video ----------
class Reader:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(str(path))
        self.cur, self.img, self.cache_idx, self.cache = -1, None, None, None

    def get(self, idx):
        while self.cur < idx:
            ok, f = self.cap.read()
            if not ok:
                break
            self.img, self.cur = f, self.cur + 1
        if self.cache_idx != self.cur:
            rgb = cv2.cvtColor(self.img, cv2.COLOR_BGR2RGB)
            self.cache = cv2.resize(rgb, (GZ_W, GZ_H), interpolation=cv2.INTER_LINEAR)
            self.cache_idx = self.cur
        return self.cache


_imgs = {}


def pimg(name):
    if name not in _imgs:
        _imgs[name] = np.asarray(Image.open(PAN / name).convert('RGB'))
    return _imgs[name]


TL = json.loads((PAN / 'timeline.json').read_text())


def right_side(seg, seg_start, s, out_t):
    cur = 0
    for i, e in enumerate(TL):
        if e['at'] <= s:
            cur = i
    e = TL[cur]
    prev = TL[cur - 1] if cur > 0 else None
    rt, pn = pimg(e['rt']).copy(), pimg(e['panel']).copy()
    if prev is not None:
        change_out = seg_start + s2o(seg, e['at'])
        p = (out_t - change_out) / WIPE
        if 0 <= p < 1:
            cut = int(640 * p)
            rt[:, cut:] = pimg(prev['rt'])[:, cut:]
            pn[:, cut:] = pimg(prev['panel'])[:, cut:]
    return rt, pn


def video_frame(reader, seg, seg_start, u, caps):
    s = o2s(seg, u)
    out_t = seg_start + u
    canvas = np.empty((H, W, 3), np.uint8)
    canvas[:] = BG
    canvas[GZ_Y:GZ_Y + GZ_H, :GZ_W] = reader.get(int(round(s * FPS)))
    rt, pn = right_side(seg, seg_start, s, out_t)
    canvas[0:640, GZ_W:] = rt
    canvas[640:1080, GZ_W:] = pn
    img = Image.fromarray(canvas)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    if in_hold(seg, u):
        lab, col = 'Playback: paused 2 s (notice sent)', YELLOW
    elif seg['speed'] == 1:
        lab, col = 'Playback: real time (1\u00d7)', WHITE
    else:
        lab, col = 'Playback: %d\u00d7 speed' % seg['speed'], ORANGE
    tw = d.textlength(lab, font=F(26, True))
    d.rounded_rectangle([16, 16, 16 + tw + 28, 62], radius=10, fill=(0, 0, 0, 170))
    d.text((30, 24), lab, font=F(26, True), fill=col + (255,))
    if 'camera' in seg and seg['camera'][0] <= u < seg['camera'][1]:
        cx, cy = CAM_RAW[0] * GZ_W / 1200.0, GZ_Y + CAM_RAW[1] * GZ_H / 952.0
        t1 = 'Fixed camera (machine-vision type)'
        t2 = 'oblique view ~54\u00b0'
        bx, by = 640, 210
        w1 = max(d.textlength(t1, font=F(26, True)), d.textlength(t2, font=F(24)))
        d.rounded_rectangle([bx, by, bx + w1 + 28, by + 84], radius=10, fill=(0, 0, 0, 170))
        d.text((bx + 14, by + 10), t1, font=F(26, True), fill=WHITE + (255,))
        d.text((bx + 14, by + 46), t2, font=F(24), fill=WHITE + (255,))
        d.line([bx + w1 * 0.7, by + 84, cx - 10, cy - 30], fill=WHITE + (230,), width=3)
    active = [c for c in caps if c['t0'] - 0.2 <= out_t <= c['t0'] + c['dur'] + 0.6]
    if active:
        c = max(active, key=lambda c: c['t0'])
        now = out_t - c['t0']
        top = 1080 - 30 - c['rows'] * 44 - 20
        d.rounded_rectangle([40, top, 1240, 1060], radius=12, fill=(0, 0, 0, 175))
        for x, y, t, font, w in c['items']:
            d.text((x, top + 14 + y), t, font=font, fill=wcol(w, now) + (255,))
    img = Image.alpha_composite(img.convert('RGBA'), ov).convert('RGB')
    return np.asarray(img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--until', type=float, default=None)
    ap.add_argument('--out', default='final.mp4')
    a = ap.parse_args()
    OUTD.mkdir(parents=True, exist_ok=True)

    t, plan, caps, audio_places = 0.0, [], [], []
    for seg in EDL:
        if seg['kind'] == 'card':
            nd = narr(seg['narr'])
            dur = seg['at'] + nd['duration'] + seg['tail']
            plan.append((seg, t, dur, build_card(seg['card'], nd)))
            audio_places.append((seg['narr'], t + seg['at'], nd['duration']))
        else:
            dur = s2o(seg, seg['src'][1])
            plan.append((seg, t, dur, None))
            for cid, sa in seg['caps']:
                nd = narr(cid)
                t0 = t + s2o(seg, sa)
                items, yend = layout(nd['words'], F(32), 60, 0, 1160, 44)
                caps.append(dict(id=cid, t0=t0, dur=nd['duration'], items=items, rows=int(round(yend / 44))))
                audio_places.append((cid, t0, nd['duration']))
        t += dur
    total = t
    print('segment plan:')
    for seg, st, dur, _ in plan:
        print('  %-6s %-8s out %6.1f - %6.1f (%5.1f s)' % (
            seg['kind'], seg.get('card', '%gx' % seg.get('speed', 1)), st, st + dur, dur))
    print('total %.1f s (%d:%04.1f)' % (total, int(total // 60), total % 60))
    audio_places.sort(key=lambda x: x[1])
    for (i1, s1, d1), (i2, s2, _) in zip(audio_places, audio_places[1:]):
        if s1 + d1 > s2:
            print('  WARNING narration overlap: %s ends %.2f > %s starts %.2f' % (i1, s1 + d1, i2, s2))

    end = total if a.until is None else min(total, a.until)
    track = np.zeros(int(np.ceil(end * SR)) + SR, np.float32)
    for nid, st, _ in audio_places:
        with wave.open(str(NAR / (nid + '.wav'))) as wf:
            x = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768.0
        i0 = int(st * SR)
        if i0 >= len(track):
            continue
        n = min(len(x), len(track) - i0)
        track[i0:i0 + n] += x[:n]
    apath = OUTD / (Path(a.out).stem + '_audio.wav')
    with wave.open(str(apath), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())

    out = OUTD / a.out
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                           '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-', '-i', str(apath),
                           '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                           '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest', str(out)],
                          stdin=subprocess.PIPE)
    reader = Reader(RAW)
    n_frames = int(round(end * FPS))
    for fi in range(n_frames):
        ot = fi / FPS
        for seg, st, dur, cache in plan:
            if st <= ot < st + dur:
                break
        u = ot - st
        frame = card_frame(cache, seg, u, dur) if seg['kind'] == 'card' else video_frame(reader, seg, st, u, caps)
        ff.stdin.write(frame.tobytes())
        if fi % 300 == 0:
            print('  frame %d / %d' % (fi, n_frames), flush=True)
    ff.stdin.close()
    ff.wait()
    print('wrote', out)


if __name__ == '__main__':
    main()
