"""Tune against leave-one-line-out rather than by feel."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import learn_style, render_style
from render_style import script_for
from evaluate import load_hand

hand = load_hand()

def score(use_ctx, back_w):
    render_style.BACK_W = back_w
    exact = close = tot = 0
    for line, theirs in hand:
        (cnt, head), _ = learn_style.build(skip=line)
        learn_style.save(cnt, head)
        mine = script_for(line, render_style.load_style(), use_ctx=use_ctx)
        for x, y in zip(theirs.lower().split(), mine.split()):
            tot += 1
            if x == y: exact += 1
            elif x[:3] == y[:3] or x[-3:] == y[-3:]: close += 1
    return exact, close, tot

print(f"{'ctx':>5} {'back_w':>7} | {'exact':>5} {'close':>5} {'score':>6}")
print("-" * 36)
best = None
for use_ctx in (False, True):
    for back_w in (0.1, 0.25, 0.45, 0.8, 1.5):
        e, c, t = score(use_ctx, back_w)
        v = e + 0.5 * c
        print(f"{str(use_ctx):>5} {back_w:7.2f} | {e:5d} {c:5d} {v:6.1f}")
        if best is None or v > best[0]: best = (v, use_ctx, back_w, e, c, t)
        if not use_ctx: break          # back_w barely matters without context
print(f"\nbest: use_ctx={best[1]} back_w={best[2]} -> {best[3]} exact, {best[4]} close of {best[5]}")
learn_style.save(*learn_style.build()[0])
