"""Build the /decks pages for the portfolio mirror.

Usage: python3 build_decks.py OUT_STATIC_DIR
Expects slide images already at OUT_STATIC_DIR/decks/<slug>-slides/NN.webp and the
PDF at OUT_STATIC_DIR/decks/<slug>.pdf.
"""
import html
import json
import os
import sys

DECKS = [
    {
        "slug": "vip-app",
        "title": "UofM VIP App",
        "figma": "https://www.figma.com/deck/503Qlz2bTdoyFQcnQi85qL/UofM-VIP-App-Presentation",
    },
    {
        "slug": "umgpt",
        "title": "UMGPT",
        "figma": "https://www.figma.com/deck/ACFTsV3pUULP7yZoHkb7nZ/UMGPT-Presentation",
    },
]

STYLE = """
:root{--bg:#0e0e10;--panel:#18181b;--line:#2a2a2e;--text:#f4f4f5;--muted:#a1a1aa;--accent:#ffffff}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--text);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;display:flex;flex-direction:column}
a{color:inherit}
header{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:14px 20px;border-bottom:1px solid var(--line)}
header .back{color:var(--muted);text-decoration:none;font-size:14px}header .back:hover{color:var(--text)}
header h1{font-size:17px;font-weight:600;margin:0 auto 0 8px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border:1px solid var(--line);border-radius:999px;background:var(--panel);text-decoration:none;font-size:14px;cursor:pointer;color:var(--text)}
.btn:hover{border-color:#52525b}.btn.primary{background:var(--accent);color:#0e0e10;border-color:var(--accent)}
"""

VIEWER = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>{title} presentation | Jaden Bachrach</title>
<style>{style}
main{{flex:1;display:flex;align-items:center;justify-content:center;padding:20px 64px;position:relative;min-height:0}}
.stage{{width:100%;max-width:calc((100vh - 230px) * 16 / 9);aspect-ratio:16/9;background:#000;border-radius:10px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,.5)}}
.stage img{{width:100%;height:100%;object-fit:contain;display:block}}
.nav{{position:absolute;top:50%;transform:translateY(-50%);width:44px;height:44px;border-radius:50%;border:1px solid var(--line);background:var(--panel);color:var(--text);font-size:22px;cursor:pointer}}
.nav:hover{{border-color:#52525b}}.nav:disabled{{opacity:.3;cursor:default}}.prev{{left:12px}}.next{{right:12px}}
.bar{{display:flex;align-items:center;justify-content:center;gap:16px;padding:0 20px 8px;color:var(--muted);font-size:14px}}
.thumbs{{display:flex;gap:8px;overflow-x:auto;padding:8px 20px 16px;scrollbar-width:thin}}
.thumbs button{{flex:0 0 auto;width:128px;aspect-ratio:16/9;padding:0;border:2px solid transparent;border-radius:6px;overflow:hidden;background:#000;cursor:pointer;opacity:.6}}
.thumbs button.on{{border-color:var(--accent);opacity:1}}.thumbs img{{width:100%;height:100%;object-fit:cover;display:block}}
:fullscreen main{{padding:0}}:fullscreen .stage{{max-width:calc(100vh * 16 / 9);border-radius:0}}
@media (max-width:700px){{main{{padding:12px}}.nav{{display:none}}.stage{{max-width:100%}}}}
</style></head>
<body>
<header>
  <a class="back" href="../">&larr; Portfolio</a>
  <h1>{title} presentation</h1>
  <a class="btn primary" href="{figma}" target="_blank" rel="noopener">Open in Figma (with animations)</a>
  <a class="btn" href="{slug}.pdf" download>Download PDF</a>
  <button class="btn" id="fs" type="button">Full screen</button>
</header>
<main>
  <button class="nav prev" id="prev" aria-label="Previous slide">&#8249;</button>
  <div class="stage" id="stage"><img id="slide" src="{slug}-slides/01.webp" alt="Slide 1 of {count}"></div>
  <button class="nav next" id="next" aria-label="Next slide">&#8250;</button>
</main>
<div class="bar"><span id="count">1 / {count}</span><span>Use arrow keys to move between slides</span></div>
<nav class="thumbs" id="thumbs" aria-label="Slides"></nav>
<script>
(function(){{
  var n={count}, i=0, slug={slug_js};
  function src(k){{return slug+"-slides/"+String(k+1).padStart(2,"0")+".webp";}}
  var img=document.getElementById("slide"), cnt=document.getElementById("count"),
      prev=document.getElementById("prev"), next=document.getElementById("next"),
      thumbs=document.getElementById("thumbs");
  for(var k=0;k<n;k++){{
    var b=document.createElement("button"); b.type="button"; b.setAttribute("aria-label","Slide "+(k+1));
    b.innerHTML='<img loading="lazy" alt="" src="'+src(k)+'">';
    b.onclick=(function(k){{return function(){{go(k);}};}})(k); thumbs.appendChild(b);
  }}
  function go(k){{
    i=Math.max(0,Math.min(n-1,k)); img.src=src(i); img.alt="Slide "+(i+1)+" of "+n;
    cnt.textContent=(i+1)+" / "+n; prev.disabled=i===0; next.disabled=i===n-1;
    Array.prototype.forEach.call(thumbs.children,function(t,j){{t.className=j===i?"on":"";}});
    var t=thumbs.children[i]; if(t&&t.scrollIntoView) t.scrollIntoView({{block:"nearest",inline:"center"}});
    if(i+1<n) new Image().src=src(i+1);
    try{{history.replaceState(null,"","#"+(i+1));}}catch(e){{}}
  }}
  prev.onclick=function(){{go(i-1);}}; next.onclick=function(){{go(i+1);}};
  document.getElementById("stage").onclick=function(e){{var r=this.getBoundingClientRect(); go(e.clientX-r.left<r.width/3?i-1:i+1);}};
  document.addEventListener("keydown",function(e){{
    if(e.key==="ArrowRight"||e.key===" "||e.key==="PageDown"){{e.preventDefault();go(i+1);}}
    else if(e.key==="ArrowLeft"||e.key==="PageUp"){{e.preventDefault();go(i-1);}}
    else if(e.key==="Home"){{go(0);}} else if(e.key==="End"){{go(n-1);}}
  }});
  document.getElementById("fs").onclick=function(){{
    var el=document.documentElement;
    if(document.fullscreenElement) document.exitFullscreen(); else if(el.requestFullscreen) el.requestFullscreen();
  }};
  var h=parseInt((location.hash||"").slice(1),10); go(h>0?h-1:0);
}})();
</script>
</body></html>
"""

INDEX = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>Presentations | Jaden Bachrach</title>
<style>{style}
.wrap{{max-width:1000px;margin:0 auto;padding:28px 20px 60px;width:100%}}
.wrap p{{color:var(--muted);margin:0 0 24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
.card a.cover{{display:block;aspect-ratio:16/9;background:#000}}.card img{{width:100%;height:100%;object-fit:cover;display:block}}
.card .body{{padding:14px 16px;display:flex;flex-direction:column;gap:10px}}
.card h2{{font-size:16px;margin:0}}.card .row{{display:flex;gap:8px;flex-wrap:wrap}}
</style></head>
<body>
<header><a class="back" href="../">&larr; Portfolio</a><h1>Presentations</h1></header>
<div class="wrap">
<p>Each deck opens here slide by slide. The Figma version has the animations, and the PDF is there to download.</p>
<div class="grid">
{cards}
</div></div>
</body></html>
"""

CARD = """<div class="card">
  <a class="cover" href="{slug}"><img src="{slug}-slides/01.webp" alt="{title} title slide" loading="lazy"></a>
  <div class="body"><h2>{title}</h2><div class="row">
    <a class="btn primary" href="{slug}">View slides ({count})</a>
    <a class="btn" href="{figma}" target="_blank" rel="noopener">Figma</a>
    <a class="btn" href="{slug}.pdf" download>PDF</a>
  </div></div>
</div>"""


def main(out):
    decks_dir = os.path.join(out, "decks")
    cards = []
    for d in DECKS:
        imgs = sorted(f for f in os.listdir(os.path.join(decks_dir, d["slug"] + "-slides")) if f.endswith(".webp"))
        count = len(imgs)
        assert count and imgs[0] == "01.webp", d["slug"]
        assert os.path.exists(os.path.join(decks_dir, d["slug"] + ".pdf")), d["slug"]
        fields = dict(title=html.escape(d["title"]), figma=html.escape(d["figma"]), slug=d["slug"],
                      count=count, style=STYLE, slug_js=json.dumps(d["slug"]))
        with open(os.path.join(decks_dir, d["slug"] + ".html"), "w") as f:
            f.write(VIEWER.format(**fields))
        cards.append(CARD.format(**fields))
        print(d["slug"], count, "slides")
    with open(os.path.join(decks_dir, "index.html"), "w") as f:
        f.write(INDEX.format(style=STYLE, cards="\n".join(cards)))


if __name__ == "__main__":
    main(sys.argv[1])
