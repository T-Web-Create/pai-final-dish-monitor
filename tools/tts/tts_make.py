#!/usr/bin/env python3
"""Synthesize all narration segments with Kokoro (af_heart) and save word timestamps.
Output: recordings/video/narr/<id>.wav, <id>.json, and all_review.wav (all segments with gaps)."""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

SR = 24000
VOICE = 'af_heart'
OUT = Path('/mnt/llm-storage/pai-final/recordings/video/narr')

SEGMENTS = [
    ('intro', 'card', [
        'Weekend colony watch.',
        'A robot that checks anaerobic culture dishes while the researcher is away.',
        'Colonies take one to three days to appear. Dishes inoculated on Friday are not seen again until Monday.',
        'A robot arm and a fixed camera check the dish every six hours, through the closed lid.',
        'The lid is opened only when needed, because the chamber is not sterile.',
        'This is a simulation with ROS 2, Gazebo, a UR3e arm and synthetic dish images. '
        'Robot motion is shown at real time or five times speed.',
    ]),
    ('s0_fri0900', 'caption', [
        'Friday, 9 a.m. Inoculated. The lid is opened once to take a reference image.',
    ]),
    ('s1_fri_pm', 'caption', [
        'Friday afternoon and evening. Checks through the closed lid show no change. The researcher leaves at 6 p.m.',
        'The bright bands are reflections of the ceiling lights. They never change, so they are ignored.',
    ]),
    ('s2_sat0300', 'caption', [
        'Saturday, 3 a.m. Something appears. Suspected: a notice is sent with a photo through the lid. The lid stays closed.',
    ]),
    ('s3_sat0900', 'caption', [
        'Saturday, 9 a.m. It grows. Confirmed: the lid is opened once for a clear photo.',
    ]),
    ('s4_weekend', 'caption', [
        'Through the weekend, checks continue through the lid. Ten colonies are confirmed, with no more openings.',
    ]),
    ('monday', 'card', [
        'Monday, 9 a.m. The researcher arrives already knowing that colonies appeared early on Saturday.',
        "Monday's experiment could be planned over the weekend.",
    ]),
    ('summary', 'card', [
        'The lid was opened two times, for 17.5 seconds in 72 hours. '
        'Opening at every check would take 13 times, about 116 seconds.',
        'The first notice came a median of five hours after a colony appeared, on 30 held-out synthetic dishes.',
        'There were no false alarms on 30 colony-free synthetic dishes.',
        'Limits: the images are synthetic, and suction and camera are simulated. '
        'The system is not yet tested on real dishes.',
    ]),
]

OUT.mkdir(parents=True, exist_ok=True)
pipe = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
review, gap = [], np.zeros(int(0.8 * SR), dtype=np.float32)
total = 0.0
slow = []
ONLY = set(sys.argv[1:])
for sid, kind, lines in SEGMENTS:
    if ONLY and sid not in ONLY:
        continue
    audio_all, words, offset = [], [], 0.0
    for li, line in enumerate(lines):
        for res in pipe(line, voice=VOICE, speed=1.0):
            a = res.audio.cpu().numpy() if hasattr(res.audio, 'cpu') else np.asarray(res.audio)
            for tk in (res.tokens or []):
                st, en = tk.start_ts, tk.end_ts
                words.append(dict(text=tk.text, line=li, ws=bool(getattr(tk, 'whitespace', ' ')),
                                  start=None if st is None else round(st + offset, 3),
                                  end=None if en is None else round(en + offset, 3)))
                if st is not None and en is not None and en - st >= 0.9:
                    slow.append((sid, tk.text, round(en - st, 2)))
            audio_all.append(a.astype(np.float32))
            offset += len(a) / SR
        if li < len(lines) - 1:
            pause = np.zeros(int(0.35 * SR), dtype=np.float32)
            audio_all.append(pause)
            offset += len(pause) / SR
    wav = np.concatenate(audio_all)
    sf.write(OUT / (sid + '.wav'), wav, SR)
    dur = len(wav) / SR
    n_none = sum(1 for w in words if w['start'] is None)
    (OUT / (sid + '.json')).write_text(json.dumps(
        dict(id=sid, kind=kind, lines=lines, duration=round(dur, 3), words=words), indent=1))
    print('%-12s %-7s %5.2f s  words %3d  no-time %d' % (sid, kind, dur, len(words), n_none))
    total += dur
    review += [wav, gap]
if not ONLY:
    sf.write(OUT / 'all_review.wav', np.concatenate(review), SR)
print('total narration %.1f s' % total)
print('words taking >= 0.9 s (check pronunciation):')
for s in slow:
    print('  %-12s %-14s %.2f s' % s)
