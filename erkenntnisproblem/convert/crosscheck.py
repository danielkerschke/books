"""Cross-check proofread pages against independent OCR text of the same pages.

    python crosscheck.py v3 work/v3-alt-ocr                 # one witness
    python crosscheck.py v2 work/v2-ocr work/v2-alt-ocr     # two witnesses (recommended)

Both proof and OCR are reduced to a stream of letters (markup, punctuation, spaces and the running
head removed, line-end hyphenation undone, lowercase) and aligned.

One witness: every disagreement is listed (after filtering typical OCR noise). Good when the
witness is a clean OCR (e.g. the 1923 Vol. III scan).

Two witnesses: only spots where BOTH OCRs disagree with the proof in the same way are listed.
Two independent scans/OCR engines rarely make the same mistake, so these are the spots most likely
to be real errors in the proof — even when each OCR on its own is very noisy.
"""
import difflib, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))

def norm_word(w):
    w = unicodedata.normalize('NFC', w)
    return w.replace('ſ', 's').replace('ﬁ', 'fi').replace('ﬂ', 'fl')

def words(text):
    text = re.sub(r'(\w)[-⸗]\s*\n\s*(\w)', r'\1\2', text)          # undo hyphenation at line ends
    text = re.sub(r'<[^>]+>|\[\^[^\]]*\]|\{\?|\}', ' ', text)        # markup, note refs, {? }
    text = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰*•]', ' ', text)                      # superscript note marks in OCR
    return [norm_word(w) for w in re.findall(r'[A-Za-zÀ-ÿĀ-ſͰ-Ͽἀ-῿]+|\d+', text)]

def proof_words(path):
    t = open(path, encoding='utf-8').read()
    t = re.sub(r'^(#{1,4} |\+ |> )', '', t, flags=re.M)
    return words(t)

def other_words(path, page_no):
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    out, skipping = [], True
    for l in lines:
        s = l.strip()
        if skipping:                                                      # running head + page number
            if not s: continue
            if re.fullmatch(r'\d{1,3}', s) or len(s) < 70 and re.search(r'(^|\s)%d(\s|$)' % page_no, s):
                skipping = False; continue
            if len(out) == 0 and len(s) < 70:
                continue
            skipping = False
        if 'Digitized by' in s or s in ('Google', 'Digitized by Google'):
            continue
        out.append(l)
    return words('\n'.join(out))

def strip_marks(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c))

def disagreements(a, b, filter_noise=True):
    """Alignment of proof letters a against OCR letters b -> list of (i1, i2, replacement)."""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal': continue
        pa, pb = a[i1:i2], b[j1:j2]
        if filter_noise:
            if tag == 'insert' and (j2 - j1 <= 2 or i1 == 0): continue
            if tag == 'delete' and i2 - i1 > 30: continue
            if tag == 'replace' and strip_marks(pa) == strip_marks(pb): continue
            if tag == 'replace' and re.fullmatch(r'[il1|]+', pa + pb): continue
            if tag == 'replace' and len(pa) == len(pb) == 1 and {pa, pb} in ({'c', 'e'}, {'n', 'h'}, {'u', 'n'}): continue
            if tag == 'insert' and re.fullmatch(r'[\d]+', pb): continue          # superscript note numbers
            if tag == 'replace' and {pa, pb} in ({'m', 'rn'}, {'l', '1'}, {'ll', '11'}, {'ii', 'ü'}, {'cl', 'd'}): continue
        out.append((i1, i2, pb))
    return out

def letters(ws):
    return ''.join(ws).lower()

def main():
    vol, witnesses = sys.argv[1], sys.argv[2:]
    proof_dir = os.path.join(HERE, 'proof', vol)
    total, pages = 0, 0
    for f in sorted(os.listdir(proof_dir)):
        if not re.fullmatch(r'p\d{3}\.md', f): continue
        n = int(f[1:4])
        paths = [os.path.join(HERE, w, 'p%03d.txt' % n) for w in witnesses]
        if not all(os.path.exists(p) for p in paths): continue
        a = letters(proof_words(os.path.join(proof_dir, f)))
        if not a: continue
        sets = [disagreements(a, letters(other_words(p, n)), filter_noise=True) for p in paths]
        if len(sets) == 1:
            found = sets[0]
        else:
            # keep a spot only if every witness disagrees with the proof at the same place in the same way
            found = [d for d in sets[0] if all(d in s for s in sets[1:])]
            found = [d for d in found if not (d[1] - d[0] > 30 and not d[2])]   # both OCRs skipped a block
        if found:
            pages += 1; total += len(found)
            print('== %s  spots %d' % (f[:-3], len(found)))
            for i1, i2, rep in found:
                print('   …%s[%s → %s]%s' % (a[max(0, i1 - 18):i1], a[i1:i2] or '∅', rep or '∅', a[i2:i2 + 12]))
    print('total spots:', total, 'pages:', pages, file=sys.stderr)

if __name__ == '__main__':
    main()
