# Proofreading spec — Cassirer, *Das Erkenntnisproblem*

Volumes (archive.org scans, Berlin: Bruno Cassirer):

| vol | edition | pages |
|-----|---------|-------|
| `v1` | Erster Band, 2nd ed. 1911 | `rV`…`rX` (Vorrede), `p001`…`p601` |
| `v2` | Zweiter Band, 3rd ed. 1922 | `p001`…`p762` (the Register after p762 is not proofread) |
| `v3` | Dritter Band (Die nachkantischen Systeme), 1920 | `rV`…`rVIII` (Vorwort), `p001`…`p483` |

For each assigned page you get two inputs:

- `work/<vol>-img/<page>.jpg` — the page scan. **The scan is the authority.**
- `work/<vol>-ocr/<page>.txt` — the archive.org OCR of that page (a starting point; full of errors).
- Vol. III only: `work/v3-alt/<page>.jpg` — a second, sharper scan of the same page from the
  1923 printing (identical setting and pagination). The 1920 scan is blurred on some pages: if any
  part of a page is hard to read, read it from the 1923 image instead.

Write `proof/<vol>/<page>.md` — the exact text of the page in the markup below. Read the
whole scan carefully, including the small footnote type. Correct every OCR error. Do not
modernize, normalize or "improve" Cassirer's spelling: keep the orthography as printed
(Skepticismus, transscendental, Accidens, giebt …), and keep the original's own misprints
(zoom in first to make sure they really are printed that way). Broken or damaged type where
the intended letter is obvious is read as the intended letter.

## Markup

```
+ continuation of a paragraph that began on the previous page …

A new paragraph that begins on this page (first line indented on the scan, or after a heading) …

### I. Section heading as printed

> An indented block quotation set in smaller type …

---
[^+] continuation of a footnote that began on the previous page …
[^1] Footnote 1 text …
[^2] Footnote 2 text …
```

- **Omit** the running head and the page number at the top of the page.
- **One line per paragraph.** Join the printed lines. Remove end-of-line hyphenation
  (`Unab-` / `hängigkeit` → `Unabhängigkeit`), but keep real hyphens (`Natur- und Geisteswissenschaft`).
  Vol. III prints the hyphen as a double hyphen `⸗` (OCR often shows `=`): treat it exactly like `-`,
  and write any real hyphen that remains as a plain `-`.
- **Paragraphs** are separated by one blank line.
- **Continuation:** if the first text on the page continues a paragraph from the previous page,
  start that line with `+ `. Otherwise no marker. (A first line that is not indented is a continuation.)
- **Last word broken across the page:** if the page's last line ends with a hyphenated word
  fragment, end the paragraph with the fragment and its hyphen (`… die Kraft und Unab-`).
  If the fragment is letter-spaced, the hyphen goes inside the tag: `<g>Unab-</g>`.
- **Headings:** `#` Buch, `##` Kapitel, `###` numbered/lettered sections (I., II., A., A), 1., a)),
  `####` smaller unnumbered headings (e.g. a philosopher's name set alone as a heading).
  Keep numbering and the final full stop as printed. Write a heading that is printed over several
  lines as one line, e.g. `## Erstes Kapitel. Bacon.` or `# Viertes Buch. Die Anfänge des Empirismus.`
  Only write headings that are printed on the page — never take them from the running head.
- **Headings** never get `<g>`/`<i>` tags, even when printed letter-spaced or italic.
- **Blank page:** write an empty file.
- **Emphasis:** letter-spaced type (S p e r r d r u c k) → `<g>word</g>` (write the word
  without the spaces). Italic → `<i>…</i>`. Bold → `<b>…</b>`. Names set in italics, titles, etc.
  all get the tag that matches what is printed. Tag only the spaced part of a partly spaced word.
- **Letter-spaced word boundaries:** in Sperrdruck the gap between two words is hard to see
  (`u n b e d i n g t l e t z t e r`). Split by sense: `<g>unbedingt letzter</g>`.
- **Section break** printed as `* * *` (or centred asterisks / a centred rule between paragraphs):
  write a line `***` as its own paragraph. A short rule that only ends a chapter is left out.
- **Footnote references:** the superscript `1)` (or `¹`, `*` …) in the text → `[^1]`, placed exactly
  where it is printed. Numbering restarts per page; use the printed number. If two notes on a page
  carry the same number, or a note's number does not match its reference, number them so each
  reference matches its note and mention it in your report. Asterisk notes → `[^*]` is not
  allowed: number them `[^1]`, `[^2]` … in order instead.
- **Footnotes:** after a line `---`, one line per note, `[^n] text`. A note continued from the
  previous page goes first as `[^+] text`. No `---` if the page has no notes. A note with several
  printed paragraphs is still one line. Verse lines inside a note or quote are joined with ` / `.
- **Quotation marks:** exactly as printed: „…“ and ‚…‘ in Vol. I/II (the OCR shows them as ,,..''),
  »…« and ›…‹ in Vol. III. Foreign-language quotes: keep whatever marks are printed.
  Apostrophes: `’`.
- **Greek:** write it in Unicode polytonic Greek with accents and breathings as printed.
  Latin, Italian, French, English as printed (including ligatures → plain letters, æ/œ kept).
- **Dashes:** `—` for the long dash, `–` only if printed as an en dash. Ellipsis as `. . .`
  if printed spaced.
- **Uncertain:** if you truly cannot read something, write your best reading as `{?reading}`.
  Use it sparingly — zoom in on the image region first if needed.
- **Ignore** printer's signature marks at the page foot (e.g. `10`, `10*`), library stamps, pencil
  marks, underlining, marginalia, and scanner noise.
- Superscripts other than note references (e.g. `x²`) → `<sup>2</sup>`; subscripts `<sub>`.

Return only a short report: pages done, and any `{?…}` spots or oddities worth a second look.
