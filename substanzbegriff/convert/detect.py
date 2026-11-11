"""List suspicious spots in the rendered reader, with ECW page numbers."""
import re, glob, html, collections, json, sys

R = sys.argv[1]
OUT = sys.argv[2]
FUNC = set('''der die das des dem den ein eine einer eines einem einen und oder aber als wie so ob es er sie wir ihr ich du man
in im an am auf aus bei mit nach von vom zu zum zur um für durch über unter vor hinter neben zwischen gegen ohne
ist sind war sein hat haben wird werden kann muß soll will nicht nur auch noch schon doch sich selbst hier da
wo was wer wenn dann denn daß weil nun je all alle jede jeder jedes kein keine dies diese dieser dieses jene jener
ja nein mehr sehr bloß rein bis ab ihm ihn ihre sei seit sowohl weder d h z B S f ff u a vgl the of and to a is in it as by
on be at or an that this which with from not are was for et la le de les des du en un une est qui que il et in ad est non'''.split())

files = sorted(glob.glob(R + '/kapitel-*.html')) + [R + '/vorwort.html']
vocab = collections.Counter()
texts = {}
for f in files:
    t = open(f, encoding='utf-8').read()
    texts[f] = t
    plain = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    for w in re.findall(r'[A-Za-zÄÖÜäöüß]+', plain):
        vocab[w.lower()] += 1

def known(w):
    return w.lower() in FUNC or vocab[w.lower()] >= 3

def variants(w):
    subs = [('c', 'e'), ('e', 'c'), ('rn', 'm'), ('li', 'h'), ('cl', 'd'), ('ii', 'ü'), ('1', 'l'), ('0', 'o'), ('n', 'u'), ('u', 'n'), ('I', 'l'), ('f', 't'), ('t', 'f'), ('a', 'e'), ('e', 'a')]
    out = set()
    for a, b in subs:
        for m in re.finditer(re.escape(a), w):
            out.add(w[:m.start()] + b + w[m.end():])
    return out

report = collections.defaultdict(list)
for f in files:
    name = f.replace('\\', '/').rsplit('/', 1)[1]
    t = texts[f]
    # split into chunks carrying the current ECW page
    parts = re.split(r'(<span class="pg" id="ecw-[^"]+")', t)
    page = '?'
    for part in parts:
        m = re.match(r'<span class="pg" id="ecw-([^"]+)"', part)
        if m:
            page = m.group(1); continue
        # notes section: map by note
        for nm in re.finditer(r'<li id="n(\d+)"', part):
            pass
        def add(kind, ctx_start, ctx_end, detail):
            ctx = html.unescape(re.sub(r'<[^>]+>', '', part[max(0, ctx_start - 80):ctx_end + 80]))
            report[name].append({'page': page, 'kind': kind, 'detail': detail, 'context': ' '.join(ctx.split())})
        # 1 letter-spaced spans that look fragmentary
        for m in re.finditer(r'<span class="sp">([^<]*)</span>', part):
            words = m.group(1).split()
            bad = [w for w in words if (not known(w) or (len(w) <= 3 and w.lower() not in FUNC)) and len(w) < 25]
            pairs = [a + b for a, b in zip(words, words[1:]) if known(a + b)]
            if bad or pairs:
                add('spaced', m.start(), m.end(), m.group(1))
        plain = re.sub(r'<sup class="fn">.*?</sup>|<span class="p[gb]"[^>]*></span>', '', part)
        plain = re.sub(r'<[^>]+>', '', plain)
        plain = html.unescape(plain)
        # 2 unrepaired letter-spacing
        for m in re.finditer(r'(?<!\w)(?:\w{1,2} ){3,}\w{1,3}(?!\w)', plain):
            toks = m.group(0).split()
            if sum(1 for x in toks if len(x) == 1) >= 3 and not re.search(r'\d', m.group(0)):
                ctx = plain[max(0, m.start() - 80):m.end() + 80]
                report[name].append({'page': page, 'kind': 'unspaced-run', 'detail': m.group(0), 'context': ' '.join(ctx.split())})
        # 3 stray page-bar characters between words
        for m in re.finditer(r'(?<=[a-zäöüß,;:.] )[I1l|](?= [a-zäöüßA-ZÄÖÜ])|(?<=[a-zäöüß] )[I1l|]-|-[I1l|](?= )', plain):
            ctx = plain[max(0, m.start() - 60):m.end() + 60]
            report[name].append({'page': page, 'kind': 'stray-bar', 'detail': m.group(0), 'context': ' '.join(ctx.split())})
        # 4 broken hyphenation
        for m in re.finditer(r'[a-zäöüß]{2,}- (?!und |oder |bzw|wie |als |sowie )[a-zäöüß]{2,}', plain):
            ctx = plain[max(0, m.start() - 50):m.end() + 50]
            report[name].append({'page': page, 'kind': 'hyphen', 'detail': m.group(0), 'context': ' '.join(ctx.split())})
        # 5 likely OCR misspellings (rare word whose one-letter variant is common)
        for m in re.finditer(r'[A-Za-zÄÖÜäöüß0-9]{3,}', plain):
            w = m.group(0)
            if vocab[w.lower()] > 1 and not re.search(r'\d', w): continue
            if re.fullmatch(r'\d+', w): continue
            if re.fullmatch(r'[A-Za-z]\d+', w): continue
            good = [v for v in variants(w) if vocab[v.lower()] >= 3 and len(v) >= 3]
            if good or re.search(r'[a-zäöü][0-9][a-zäöü]', w):
                ctx = plain[max(0, m.start() - 50):m.end() + 50]
                report[name].append({'page': page, 'kind': 'ocr-word', 'detail': w + (' -> ' + '/'.join(sorted(good)[:3]) if good else ''), 'context': ' '.join(ctx.split())})
        # 6 garbled Greek / symbol soup
        for m in re.finditer(r'\S*[{}!/\\]\S*[a-z]\S*(?: \S+){0,3}', plain):
            if re.search(r'https?:|\d/\d|II/|I/', m.group(0)): continue
            ctx = plain[max(0, m.start() - 40):m.end() + 60]
            report[name].append({'page': page, 'kind': 'garbled', 'detail': m.group(0), 'context': ' '.join(ctx.split())})

total = 0
for name in report:
    seen = set(); uniq = []
    for r in report[name]:
        k = (r['kind'], r['detail'], r['context'][:60])
        if k in seen: continue
        seen.add(k); uniq.append(r)
    report[name] = uniq
    c = collections.Counter(r['kind'] for r in uniq)
    total += len(uniq)
    print(name, dict(c))
print('total', total)
json.dump(report, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
