"""Write one OCR text file per book page, and rename the rendered page images to book page names.

    python ocrpages.py v2

PDF page -> book page mapping per volume (offset = pdf page of book page 1, minus 1).
"""
import json, os, sys

ROMAN = ['V', 'VI', 'VII', 'VIII', 'IX', 'X']
VOLS = {
    'v1': dict(roman=(9, 6), offset=24, last=601),
    'v2': dict(roman=None, offset=20, last=762),
    'v3': dict(roman=(9, 4), offset=20, last=483),
}
v = sys.argv[1]
C = VOLS[v]
HERE = os.path.dirname(os.path.abspath(__file__))
work = os.path.join(HERE, 'work')

def name_of(pdf):
    if C['roman'] and C['roman'][0] <= pdf < C['roman'][0] + C['roman'][1]:
        return 'r' + ROMAN[pdf - C['roman'][0]]
    n = pdf - C['offset']
    return 'p%03d' % n if 1 <= n <= C['last'] else None

pages = json.load(open(os.path.join(work, v + '-pages.json'), encoding='utf-8'))
os.makedirs(os.path.join(work, v + '-ocr'), exist_ok=True)
n = 0
for p in pages:
    name = name_of(p['pdf'])
    if name:
        with open(os.path.join(work, v + '-ocr', name + '.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(l['text'] for l in p['lines']) + '\n')
        n += 1
print(v, 'ocr pages:', n)

img = os.path.join(work, v + '-img')
renamed = removed = 0
for f in sorted(os.listdir(img)) if os.path.isdir(img) else []:
    if not f.startswith('pdf-'):
        continue
    name = name_of(int(f[4:-4]))
    if name:
        os.replace(os.path.join(img, f), os.path.join(img, name + '.jpg')); renamed += 1
    else:
        os.remove(os.path.join(img, f)); removed += 1
print(v, 'images renamed:', renamed, 'removed:', removed)
