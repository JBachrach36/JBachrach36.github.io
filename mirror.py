"""Make a self-contained static copy of a published Framer site.

Every page is saved as HTML. Every image, font, stylesheet and script the
site loads from Framer's CDN (or Google Fonts) is downloaded into the copy,
and all references are rewritten to point at the copy, so a visitor whose
network blocks Framer's domains still sees the full site.

Settings come from environment variables:
  SOURCE_URL  the live Framer site, e.g. https://name.framer.website
  MIRROR_URL  where the copy will be served, e.g. https://name.github.io
  OUT_DIR     output folder (default: site)
"""
import concurrent.futures as cf
import os
import posixpath
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SOURCE_URL = os.environ["SOURCE_URL"].rstrip("/")
MIRROR_URL = os.environ["MIRROR_URL"].rstrip("/")
OUT_DIR = os.environ.get("OUT_DIR", "site")

# Hosts whose files get copied into the mirror under /_ext/<host>/...
ASSET_HOSTS = [
    "framerusercontent.com",
    "fonts.gstatic.com",
    "fonts.googleapis.com",
    "app.framerstatic.com",
    "framer.com/m",  # older Framer component modules
]
# Overridable for testing: maps a real host to the base URL actually fetched.
FETCH_OVERRIDE = {}

SRC = urllib.parse.urlsplit(SOURCE_URL)
TEXT_EXT = (".mjs", ".js", ".css", ".json", ".html", ".svg", ".txt")
UA = "Mozilla/5.0 (portfolio-mirror; GitHub Actions)"

_host_alt = "|".join(re.escape(h) for h in ASSET_HOSTS)
ASSET_RE = re.compile(r"https?://(?:%s)/[^\s\"'()<>\\`,]+" % _host_alt)
REL_IMPORT_RE = re.compile(r"""["'`](\.{1,2}/[^"'`\s]+?\.(?:mjs|js|css|json))["'`]""")
HREF_RE = re.compile(r"""href=["']([^"'#?]*)""")
LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")


def fetch(url, tries=3):
    real = url
    for host, base in FETCH_OVERRIDE.items():
        prefix = "https://" + host
        if real.startswith(prefix):
            real = base + real[len(prefix):]
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(real, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            last = e
        except Exception as e:  # network hiccup: retry
            last = e
        time.sleep(1.5 * (i + 1))
    raise last


def asset_local_path(url):
    """https://framerusercontent.com/images/a.png?x=1 -> _ext/framerusercontent.com/images/a.png"""
    p = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(p.path)
    if path.endswith("/") or not path:
        path += "index"
    clean = posixpath.normpath(p.netloc + path).lstrip("/")
    if clean.startswith(".."):
        raise ValueError("bad path: " + url)
    return posixpath.join("_ext", clean)


def page_local_path(path):
    """/ -> index.html, /about -> about.html, /work/x -> work/x.html, /404 -> 404.html"""
    path = urllib.parse.unquote(path).strip("/")
    if not path:
        return "index.html"
    clean = posixpath.normpath(path)
    if clean.startswith(".."):
        raise ValueError("bad page path: " + path)
    return clean + ".html"


def write(rel, data):
    full = os.path.join(OUT_DIR, rel)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "wb") as f:
        f.write(data)


def is_text(url):
    return urllib.parse.urlsplit(url).path.lower().endswith(TEXT_EXT) or "fonts.googleapis.com" in url


def find_assets(text, base_url=None):
    found = set()
    norm = text.replace("\\/", "/").replace("&amp;", "&")
    for m in ASSET_RE.finditer(norm):
        found.add(m.group(0).rstrip(".;"))
    if base_url:
        for m in REL_IMPORT_RE.finditer(text):
            found.add(urllib.parse.urljoin(base_url, m.group(1)))
    return found


# Figma links to send to pages inside the mirror instead, so they work on
# networks that block figma.com. Format: "FILEKEY=/path,FILEKEY2=/path2"
DECK_LINKS = {}
for _pair in filter(None, os.environ.get("DECK_LINKS", "").split(",")):
    _key, _path = _pair.strip().split("=", 1)
    DECK_LINKS[_key] = _path


def _deck_sub(m):
    escaped = "\\/" in m.group(0)
    url = MIRROR_URL + DECK_LINKS[m.group("key")]
    return url.replace("/", "\\/") if escaped else url


DECK_RE = None
if DECK_LINKS:
    DECK_RE = re.compile(
        r"https?:(?:\\?/){2}(?:www\.)?figma\.com(?:\\?/)(?:deck|slides|proto|design|file)(?:\\?/)"
        r"(?P<key>%s)[^\"'\s<>()`]*" % "|".join(re.escape(k) for k in DECK_LINKS)
    )


def rewrite(text):
    if DECK_RE:
        text = DECK_RE.sub(_deck_sub, text)
    for host in ASSET_HOSTS:
        new = "%s/_ext/%s/" % (MIRROR_URL, host)
        text = text.replace("https://%s/" % host, new)
        text = text.replace("https:\\/\\/%s\\/" % host.replace("/", "\\/"), new.replace("/", "\\/"))
        text = text.replace("//%s/" % host, new)  # protocol-relative
    text = text.replace(SOURCE_URL + "/", MIRROR_URL + "/").replace(SOURCE_URL, MIRROR_URL)
    return text


# Injected into every page: keep the copy out of search results (the real site
# stays the canonical one) and make sure entrance animations can never leave
# content invisible if a script fails to load.
HEAD_EXTRA = """
<meta name="robots" content="noindex">
<link rel="canonical" href="{canonical}">
<style id="mirror-appear-fallback-css">.mirror-force-visible{{opacity:1!important;transform:none!important;filter:none!important;visibility:visible!important}}</style>
<noscript><style>[data-framer-appear-id]{{opacity:1!important;transform:none!important;filter:none!important}}</style></noscript>
<script>
setTimeout(function(){{try{{document.querySelectorAll('[data-framer-appear-id],[style*="opacity:0"],[style*="opacity: 0"]').forEach(function(el){{if(parseFloat(getComputedStyle(el).opacity)===0)el.classList.add('mirror-force-visible');}});}}catch(e){{}}}},3000);
</script>
"""


def crawl_pages():
    pages, queue, seen = {}, ["/"], set()
    try:
        sm = fetch(SOURCE_URL + "/sitemap.xml").decode("utf-8", "replace")
        for loc in LOC_RE.findall(sm):
            p = urllib.parse.urlsplit(loc)
            queue.append(p.path or "/")
    except Exception as e:
        print("no sitemap (%s), crawling links only" % e)
    queue.append("/404")
    while queue:
        path = queue.pop(0)
        path = "/" + path.strip("/")
        if path in seen:
            continue
        seen.add(path)
        url = SOURCE_URL + (path if path != "/" else "/")
        try:
            html = fetch(url).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if path == "/404" and e.code == 404:
                html = e.read().decode("utf-8", "replace") if hasattr(e, "read") else ""
                if not html:
                    continue
            else:
                print("skip page %s (%s)" % (path, e))
                continue
        pages[path] = html
        print("page", path)
        for href in HREF_RE.findall(html):
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            absu = urllib.parse.urljoin(url if path != "/" else SOURCE_URL + "/", href)
            p = urllib.parse.urlsplit(absu)
            if p.netloc != SRC.netloc:
                continue
            last = p.path.rsplit("/", 1)[-1]
            if "." in last:  # a file, not a page
                continue
            queue.append(p.path or "/")
    return pages


def main():
    pages = crawl_pages()
    if "/" not in pages:
        sys.exit("Could not load the home page; leaving the current mirror untouched.")

    todo = set()
    for html in pages.values():
        todo |= find_assets(html)

    done, failed = set(), []
    while todo:
        batch = [u for u in todo if u not in done]
        todo = set()
        if not batch:
            break
        with cf.ThreadPoolExecutor(max_workers=16) as ex:
            futs = {ex.submit(fetch, u): u for u in batch}
            for fut in cf.as_completed(futs):
                u = futs[fut]
                done.add(u)
                try:
                    data = fut.result()
                except Exception as e:
                    failed.append((u, str(e)))
                    continue
                rel = asset_local_path(u)
                if is_text(u):
                    text = data.decode("utf-8", "replace")
                    todo |= {x for x in find_assets(text, base_url=u.split("?")[0]) if x not in done}
                    data = rewrite(text).encode("utf-8")
                write(rel, data)

    for path, html in pages.items():
        canonical = SOURCE_URL + (path if path != "/" else "/")
        html = rewrite(html)
        extra = HEAD_EXTRA.format(canonical=canonical)
        if "</head>" in html:
            html = html.replace("</head>", extra + "</head>", 1)
        else:
            html = extra + html
        name = "404.html" if path == "/404" else page_local_path(path)
        write(name, html.encode("utf-8"))
        # A page that also has sub-pages (/work and /work/x) needs a folder
        # index too, in case the host resolves /work to the folder.
        if path != "/" and any(p.startswith(path + "/") for p in pages):
            write(name[:-5] + "/index.html", html.encode("utf-8"))

    write(".nojekyll", b"")
    stamp = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    write("mirror-info.txt", ("Mirror of %s\nLast updated: %s\nPages: %d\nAssets: %d\n"
                              % (SOURCE_URL, stamp, len(pages), len(done) - len(failed))).encode())

    print("\n%d pages, %d assets copied" % (len(pages), len(done) - len(failed)))
    if failed:
        print("%d assets could not be fetched (usually harmless):" % len(failed))
        for u, e in failed[:40]:
            print("  ", u, "->", e)


if __name__ == "__main__":
    main()
