#!/usr/bin/env python3
"""Synthesize one sentence with Kokoro and print word timestamps."""
import numpy as np
import soundfile as sf
from kokoro import KPipeline

TEXT = 'Fri 09:00. Inoculated. The lid is opened once to take a reference image.'
pipe = KPipeline(lang_code='a')
chunks, words = [], []
offset = 0.0
for res in pipe(TEXT, voice='af_heart', speed=1.0):
    audio = res.audio.cpu().numpy() if hasattr(res.audio, 'cpu') else np.asarray(res.audio)
    for tk in (res.tokens or []):
        st, en = getattr(tk, 'start_ts', None), getattr(tk, 'end_ts', None)
        words.append((tk.text, None if st is None else st + offset, None if en is None else en + offset))
    chunks.append(audio)
    offset += len(audio) / 24000.0
wav = np.concatenate(chunks)
sf.write('test_af_heart.wav', wav, 24000)
print('duration %.2f s, chunks %d' % (len(wav) / 24000.0, len(chunks)))
for w, st, en in words:
    print('  %-12s %s - %s' % (w, '%.2f' % st if st is not None else 'None', '%.2f' % en if en is not None else 'None'))
