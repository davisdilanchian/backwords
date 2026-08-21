import sys; sys.path.insert(0, __import__('os').path.dirname(__file__) or '.')
from obj import score_script

def T(x): return f"[[{x}]]"

def rank(target, cands, label):
    print(f"\n{label}   target = {target}")
    rows = sorted((score_script(T(target), T(c)), c, note) for c, note in cands)
    for s, c, note in rows:
        print(f"   {s:.4f}  {c:12s} {note}")
    return rows[0][1]

# 1. stops: does pre-aspiration or voicing compensation beat naive reversal?
rank("t'0p", [("p'0t","naive phone reversal"), ("p'0ht","pre-aspirated final t"),
              ("b'0t","voiced onset"), ("p'0d","voiced coda"),
              ("b'0ht","voiced onset + preasp"), ("t'0p","control: target itself")],
     "[1] hear TOP")
rank("p'0t", [("t'0p","naive"), ("t'0hp","pre-asp final p"), ("d'0p","voiced onset"),
              ("t'0b","voiced coda"), ("p'0t","control: target itself")],
     "[2] hear POT")
rank("k'at", [("t'ak","naive"), ("t'ahk","pre-asp final k"), ("d'ak","voiced onset"),
              ("t'ag","voiced coda")],
     "[3] hear CAT")
rank("b'at", [("t'ab","naive"), ("t'ahb","pre-asp"), ("d'ab","voiced onset"),
              ("t'ap","devoiced coda")],
     "[4] hear BAT")
rank("d'0g", [("g'0d","naive"), ("k'0d","devoiced onset"), ("g'0t","devoiced coda"),
              ("g'0hd","pre-asp")],
     "[5] hear DOG")
