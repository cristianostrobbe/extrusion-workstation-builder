"""Build docs/index.html (GitHub Pages) from web/index.html.

web/index.html is a page fragment: it has no <!doctype>, <html>, <head> or <body>,
because claude.ai adds those when it is published as an Artifact. Static hosts need a
complete document, so this script wraps it. Run after editing the page:

    python3 web/build.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "index.html")
OUT_DIR = os.path.join(HERE, "..", "docs")

# The same small reset claude.ai puts around an Artifact, so the page renders identically.
RESET = (":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);"
         "padding-bottom:env(safe-area-inset-bottom,0px)}"
         "body{margin:0;font:14px/1.4 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}"
         "img{max-width:100%}[hidden]{display:none!important}")

src = open(SRC, encoding="utf-8").read()
split = src.index('<div class="wrap">')          # everything before it belongs in <head>
head, body = src[:split].strip(), src[split:].strip()
head = head.replace('<meta charset="utf-8">', "").strip()

doc = ("<!doctype html>\n<html lang=\"en\">\n<head>\n"
       "<meta charset=\"utf-8\">\n"
       "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">\n"
       f"<style>{RESET}</style>\n{head}\n</head>\n<body>\n{body}\n</body>\n</html>\n")

os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(doc)
open(os.path.join(OUT_DIR, ".nojekyll"), "w").close()   # serve files as they are
print(f"Wrote docs/index.html ({len(doc) // 1024} KB)")
