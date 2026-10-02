"""Portable, offline HTML reading guides from the maintained Markdown sources."""
from html import escape
import mistune
from plata_risk.common import ROOT, OUTPUTS

render = mistune.create_markdown(plugins=["table"])
style = """
body{font:17px/1.65 system-ui, sans-serif;color:#172c3b;background:#f4f6f7;margin:0}
main{max-width:1000px;margin:40px auto;background:white;padding:55px 65px;border-top:8px solid #244b68}
h1{font-size:36px;line-height:1.2}h2{margin-top:2em;color:#244b68;font-size:24px}
table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:10px;border-bottom:1px solid #ced9df;text-align:left}
th{background:#eaf0f3}a{color:#155c8b}pre{overflow:auto;background:#eef2f5;padding:20px}
@media(max-width:700px){main{margin:0;padding:24px}h1{font-size:28px}table{display:block;overflow-x:auto}}
@media print{body{background:white}main{margin:0;padding:0;border:0}h2{break-after:avoid}tr{break-inside:avoid}}
"""
for source, target, lang in [("PORTFOLIO_EN.md", "portfolio_en.html", "en"),
                              ("РАЗБОР_RU.md", "explanation_ru.html", "ru")]:
    body = render((ROOT / source).read_text(encoding="utf-8"))
    body = body.replace('href="outputs/casebook.html"', 'href="casebook.html"')
    html = (f'<!doctype html><html lang="{lang}"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(source)}</title><style>{style}</style><main>{body}</main></html>')
    (OUTPUTS / target).write_text(html, encoding="utf-8")
    print(target)
