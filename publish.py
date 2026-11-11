"""Validate and publish the whole site (landing page + one subpage per book) to GitHub Pages.

    python publish.py --check   # validate only
    python publish.py           # validate, then deploy to the gh-pages branch

Site layout on the gh-pages branch:
    bibliothek/index.html       <- ./bibliothek/index.html (landing page)
    <slug>/...                  <- each book's reader folder (HTML, CSS, JS only)

Only the folders listed in FOLDERS are written. Every other file already on the
branch (e.g. the Heidegger reader at the site root) is left exactly as it is.
PDFs and conversion files are never published.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
REPOSITORY = "danielkerschke/books"
REMOTE = f"https://github.com/{REPOSITORY}.git"
BRANCH = "gh-pages"
SITE_URL = "https://danielkerschke.github.io/books/"
SUFFIXES = {".html", ".css", ".js"}

# folder on the site -> local folder (HTML, CSS, JS files are published)
FOLDERS = {
    "bibliothek": ROOT / "bibliothek",
    "substanzbegriff": ROOT / "substanzbegriff" / "reader",
    "erkenntnisproblem-1": ROOT / "erkenntnisproblem" / "reader" / "band-1",
    "erkenntnisproblem-2": ROOT / "erkenntnisproblem" / "reader" / "band-2",
    "erkenntnisproblem-3": ROOT / "erkenntnisproblem" / "reader" / "band-3",
}

# Pages already on the site that this script does not manage but may link to.
UNMANAGED = {"index.html"}


def run(*args: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=cwd, text=True, encoding="utf-8", capture_output=True)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


class Document(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.duplicates: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        identifier = attributes.get("id")
        if identifier:
            if identifier in self.ids:
                self.duplicates.append(identifier)
            self.ids.add(identifier)
        for attribute in ("href", "src"):
            if attributes.get(attribute):
                self.links.append(attributes[attribute])


def site_files() -> dict[str, Path]:
    """Map published path -> local file."""
    files = {}
    for slug, folder in FOLDERS.items():
        if not (folder / "index.html").is_file():
            raise RuntimeError(f"{folder}/index.html is missing")
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.suffix in SUFFIXES:
                files[f"{slug}/{path.name}"] = path
    return files


def validate() -> dict[str, Path]:
    files = site_files()
    docs = {name: Document(path.read_text(encoding="utf-8")) for name, path in files.items() if name.endswith(".html")}
    errors = []
    for name, doc in docs.items():
        if doc.duplicates:
            errors.append(f"{name}: duplicate IDs {doc.duplicates[:5]}")
        base = name.rsplit("/", 1)[0] + "/" if "/" in name else ""
        for link in doc.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            target = name if not url.path else str(Path(base + unquote(url.path)).as_posix())
            target = _normalise(target)
            if target in UNMANAGED:
                continue
            if target not in files:
                errors.append(f"{name}: unpublished local resource {link}")
            elif url.fragment and (target not in docs or unquote(url.fragment) not in docs[target].ids):
                errors.append(f"{name}: missing anchor {link}")
    if errors:
        raise RuntimeError("\n".join(errors))
    print(f"Validated {len(docs)} HTML pages and {len(files)} published files.")
    return files


def _normalise(path: str) -> str:
    parts: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    result = "/".join(parts)
    if path.endswith("/") or result == "" or "." not in result.rsplit("/", 1)[-1]:
        result = (result + "/index.html").lstrip("/")
    return result


def configure_pages() -> str:
    response = run("gh", "api", f"repos/{REPOSITORY}/pages", check=False)
    if response.returncode:
        raise RuntimeError(response.stderr.strip())
    settings = json.loads(response.stdout)
    source = settings.get("source", {})
    if source.get("branch") != BRANCH or source.get("path") != "/":
        raise RuntimeError("GitHub Pages has a different publishing source; no settings were changed.")
    return settings.get("html_url", SITE_URL)


def publish(files: dict[str, Path]) -> None:
    author_name = run("git", "config", "user.name").stdout.strip()
    author_email = run("git", "config", "user.email").stdout.strip()
    with tempfile.TemporaryDirectory(prefix="books-pages-") as directory:
        checkout = Path(directory).resolve()
        run("git", "init", "--initial-branch", BRANCH, cwd=checkout)
        run("git", "config", "user.name", author_name, cwd=checkout)
        run("git", "config", "user.email", author_email, cwd=checkout)
        run("git", "remote", "add", "origin", REMOTE, cwd=checkout)
        existing = run("git", "ls-remote", "--heads", "origin", BRANCH, cwd=checkout).stdout.strip()
        if existing:
            run("git", "fetch", "--depth=1", "origin", BRANCH, cwd=checkout)
            run("git", "checkout", "-B", BRANCH, "FETCH_HEAD", cwd=checkout)
            for slug in FOLDERS:  # replace only the folders this script manages
                run("git", "rm", "-r", "-q", "--ignore-unmatch", slug, cwd=checkout)
        for name, source in files.items():
            target = checkout / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if not (checkout / ".nojekyll").exists():
            (checkout / ".nojekyll").write_text("", encoding="utf-8")
        run("git", "add", "--all", cwd=checkout)
        changed = run("git", "diff", "--cached", "--quiet", cwd=checkout, check=False)
        if changed.returncode not in {0, 1}:
            raise RuntimeError(changed.stderr)
        if changed.returncode == 1 or not existing:
            run("git", "commit", "-m", "Publish site", cwd=checkout)
            run("git", "push", "origin", f"HEAD:{BRANCH}", cwd=checkout)
            print("Published commit:", run("git", "rev-parse", "HEAD", cwd=checkout).stdout.strip())
        else:
            print("Published site is already up to date.")
    print("Public site:", configure_pages())
    print("GitHub Pages may take a few minutes to finish deployment.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Validate only, without publishing")
    args = parser.parse_args()
    site = validate()
    if not args.check:
        publish(site)
