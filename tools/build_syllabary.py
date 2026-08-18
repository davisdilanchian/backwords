import os, sys, json, subprocess, collections
_p = lambda n: os.path.join(os.path.dirname(os.path.abspath(__file__)), n)
sys.path.insert(0, __import__('os').path.dirname(__file__) or '.')
from g2p import ipa_to_arpa, atomize

ONS1 = {
 "B":["b"], "CH":["ch"], "D":["d"], "DH":["th"], "F":["f","ph"], "G":["g"],
 "HH":["h"], "JH":["j"], "K":["k","c"], "L":["l"], "M":["m"], "N":["n"],
 "NG":["ng"], "P":["p"], "R":["r","wr"], "S":["s","c"], "SH":["sh"],
 "T":["t"], "TH":["th"], "V":["v"], "W":["w"], "Y":["y"], "Z":["z"], "ZH":["zh"],
}
ONS2 = {
 "S T":["st"], "S P":["sp"], "S K":["sk","sc"], "S L":["sl"], "S M":["sm"],
 "S N":["sn"], "S W":["sw"], "T R":["tr"], "D R":["dr"], "P R":["pr"],
 "B R":["br"], "K R":["cr","kr"], "G R":["gr"], "F R":["fr"], "TH R":["thr"],
 "SH R":["shr"], "P L":["pl"], "B L":["bl"], "K L":["cl","kl"], "G L":["gl"],
 "F L":["fl"], "T W":["tw"], "K W":["qu","kw"], "D W":["dw"], "S F":["sf"],
 "T S":["ts"], "D Z":["dz"], "P S":["ps"], "K S":["x"], "G Z":["gz"],
 "M Y":["mu"], "P Y":["pu"], "K Y":["cu"], "B Y":["bu"], "F Y":["fu"],
 "V R":["vr"], "Z L":["zl"], "SH T":["sht"], "SH M":["shm"], "S T R":["str"],
 "S P R":["spr"], "S K R":["scr"], "S K W":["squ"], "S P L":["spl"],
 "N Y":["ny"], "H W":["wh"], "S HH":["sh"],
}
COD1 = dict(ONS1, **{
 "CH":["tch"], "JH":["dge","ge"], "K":["ck","k"], "S":["ss","s"],
 "Z":["zz","z","ze"], "ZH":["ge"], "R":["r"], "G":["g","gg"], "NG":["ng"],
 "F":["ff","f"], "L":["ll","l"], "V":["ve","vve"], "B":["b","bb"],
 "D":["d","dd"], "TH":["th"], "M":["m","mm"], "N":["n","nn"], "P":["p","pp"],
 "T":["t","tt"], "SH":["sh"], "W":["w"], "Y":["y"], "HH":["h"],
 "DH":["the"],                      # silent e is the only reliable voiced th
})
COD2 = {
 "S T":["st"], "S P":["sp"], "S K":["sk"], "T S":["ts"], "D Z":["ds"],
 "L T":["lt"], "L D":["ld"], "L K":["lk"], "L P":["lp"], "L F":["lf"],
 "L M":["lm"], "L N":["ln"], "L S":["lse"], "L TH":["lth"], "L V":["lve"],
 "N T":["nt"], "N D":["nd"], "N K":["nk"], "N S":["nce"], "N Z":["ns"],
 "N CH":["nch"], "N JH":["nge"], "N TH":["nth"], "M P":["mp"], "M S":["ms"],
 "M F":["mf"], "NG K":["nk"], "NG Z":["ngs"], "P T":["pt"], "K T":["ct"],
 "F T":["ft"], "S T S":["sts"], "K S":["x","cks"], "P S":["ps"], "T TH":["tth"],
 "R T":["rt"], "R D":["rd"], "R K":["rk"], "R M":["rm"], "R N":["rn"],
 "R L":["rl"], "R S":["rce"], "R Z":["rs"], "R TH":["rth"], "R P":["rp"],
 "R B":["rb"], "R G":["rg"], "R F":["rf"], "R V":["rve"], "R CH":["rch"],
 "R JH":["rge"], "F S":["fs"], "TH S":["ths"], "SH T":["shed"], "S HH":["sh"],
 "Z D":["sed"], "V D":["ved"], "L Z":["lls"], "M D":["med"], "N D Z":["nds"],
 "R DH":["rthe"], "N DH":["nthe"], "L DH":["lthe"], "N Z":["ns","nz"],
 "R Z":["rs"], "M Z":["ms"], "V Z":["ves"], "R V":["rve"], "L V":["lve"],
 "N V":["nve"], "R JH":["rge"], "N JH":["nge"], "L JH":["lge"], "R ZH":["rge"],
 "R B":["rb"], "R D":["rd"], "R G":["rg"], "L B":["lb"], "L D":["ld"],
 "L G":["lg"], "N B":["nb"], "M B":["mb"], "Z M":["sm"], "Z N":["zn"],
}
NUC = {
 "AA":["ah","o","a"], "AE":["a","aa"], "AH":["u","o","uh"], "AO":["aw","au","o","augh"],
 "EH":["e","ea","eh"], "IH":["i","y","ih"], "IY":["ee","ea","e","i"], "UH":["oo","u","ou"],
 "UW":["oo","ue","u","ew"], "ER":["er","ur","ir","or"],
 "AA IY":["ie","y","igh"], "EH IY":["ay","ai"], "AO IY":["oy","oi"],
 "AA UW":["ow","ou"], "AO UW":["oa","ow"],
 "IY AH":["ea"], "AH IY":["ui"],
}
NUC["AA"] += ["aa"]; NUC["AO"] += ["awe"]; NUC["IY"] += ["eee"]
NUC["AE"] += ["aa"]; NUC["UW"] += ["ooo"]
ONS = {**{k:v for k,v in ONS1.items()}, **ONS2}
COD = {**{k:v for k,v in COD1.items()}, **COD2}

cands = collections.defaultdict(set)
def add(key, s): cands[tuple(key)].add(s)

for nk, nv in NUC.items():
    np_ = nk.split()
    for n in nv: add(np_, n)
    for ok, ov in ONS.items():
        op = ok.split()
        for o in ov:
            for n in nv: add(op+np_, o+n)
    for ck, cv in COD.items():
        cp = ck.split()
        for c in cv:
            for n in nv: add(np_+cp, n+c)
    for ok, ov in ONS.items():
        op = ok.split()
        for ck, cv in COD.items():
            cp = ck.split()
            for o in ov:
                for n in nv:
                    for c in cv: add(op+np_+cp, o+n+c)

# bare consonants: unavoidable schwa, but a known one beats a dropped phone
for ck, cv in {**ONS1, **ONS2}.items():
    for c in cv: add(ck.split()+["AH"], c+"uh")

flat = [(k, s) for k, ss in cands.items() for s in ss]
print('tuples:', len(cands), 'candidates:', len(flat))

def espeak_batch(strs, chunk=4000):
    out = []
    for i in range(0, len(strs), chunk):
        part = strs[i:i+chunk]
        r = subprocess.run(["espeak-ng","-q","--ipa","-v","en-us"],
                           input="\n".join(part), capture_output=True, text=True)
        toks = r.stdout.split()
        if len(toks) != len(part):
            toks = [subprocess.run(["espeak-ng","-q","--ipa","-v","en-us"],
                     input=w, capture_output=True, text=True).stdout.strip().replace(" ","")
                    for w in part]
        out.extend(toks)
    return out

ipas = espeak_batch([s for _, s in flat])
ver = collections.defaultdict(list)
for (key, spell), ipa in zip(flat, ipas):
    if tuple(atomize(ipa_to_arpa(ipa)[0])) == tuple(atomize(list(key))):
        ver[key].append(spell)
print('verified:', len(ver), '/', len(cands))
json.dump({" ".join(k): sorted(v, key=len) for k, v in ver.items()}, open(_p('syllabary.json'),'w'))
