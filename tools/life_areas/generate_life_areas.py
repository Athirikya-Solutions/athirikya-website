#!/usr/bin/env python3
from __future__ import annotations
import argparse, html, json, re
from pathlib import Path
from typing import Any

SITE_URL="https://athirikya.com"
OUTPUT_ROOT=Path("mygermanfreund/life-areas")
LIFE_AREAS_FILE=Path(__file__).with_name("life_areas.json")
KNOWLEDGE_UNITS_FILE=Path(__file__).with_name("knowledge_units.json")
SAFE_SLUG=re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ISSUE_ID=re.compile(r"^\d{4}-W\d{2}$")

class ValidationError(ValueError): pass
def esc(v:str)->str: return html.escape(v,quote=True)
def load_json(p:Path)->Any: return json.loads(p.read_text(encoding="utf-8"))
def require_text(v:Any,n:str)->str:
    if not isinstance(v,str) or not v.strip(): raise ValidationError(f"{n} must be a non-empty string.")
    return v.strip()
def normalize_slug(v:Any,n:str)->str:
    s=require_text(v,n)
    if not SAFE_SLUG.fullmatch(s): raise ValidationError(f"{n} must be a safe lowercase slug: {s!r}")
    return s

def validate_life_areas(raw:Any)->list[dict[str,str]]:
    if not isinstance(raw,dict) or not isinstance(raw.get("lifeAreas"),list):
        raise ValidationError("life_areas.json must contain a lifeAreas array.")
    out=[]; seen=set()
    for i,item in enumerate(raw["lifeAreas"],1):
        if not isinstance(item,dict): raise ValidationError(f"Life Area {i} must be an object.")
        aid=normalize_slug(item.get("id"),f"Life Area {i} id")
        if aid in seen: raise ValidationError(f"Duplicate Life Area id: {aid}")
        seen.add(aid)
        out.append({"id":aid,"title":require_text(item.get("title"),f"Life Area {i} title"),"description":require_text(item.get("description"),f"Life Area {i} description")})
    return out

def expected_issue_url(issue_id:str)->str:
    week=issue_id.split("-W",1)[1]
    return f"/mygermanfreund/german-buzz/kw-{int(week)}/"

def validate_experiences(raw:Any,unit_index:int,global_seen:set[tuple[str,str]])->list[dict[str,str]]:
    if raw is None: return []
    if not isinstance(raw,list): raise ValidationError(f"Knowledge Unit {unit_index} experiences must be an array.")
    out=[]
    for i,item in enumerate(raw,1):
        p=f"Knowledge Unit {unit_index} experience {i}"
        if not isinstance(item,dict): raise ValidationError(f"{p} must be an object.")
        issue=require_text(item.get("issueId"),f"{p} issueId")
        if not ISSUE_ID.fullmatch(issue): raise ValidationError(f"{p} issueId must use YYYY-W## format.")
        topic=require_text(item.get("topic"),f"{p} topic")
        url=require_text(item.get("url"),f"{p} url")
        expected_url=expected_issue_url(issue)
        if url!=expected_url:
            raise ValidationError(f"{p} url must match {issue}: expected {expected_url}, got {url}")
        key=(issue,topic.casefold())
        if key in global_seen: raise ValidationError(f"Duplicate experience across Knowledge Units: {issue} / {topic}")
        global_seen.add(key); out.append({"issueId":issue,"topic":topic,"url":url})
    return out

def validate_knowledge_units(raw:Any,valid:set[str])->list[dict[str,Any]]:
    if not isinstance(raw,list): raise ValidationError("knowledge_units.json must contain an array.")
    out=[]; seen=set(); global_experiences:set[tuple[str,str]]=set()
    for i,item in enumerate(raw,1):
        if not isinstance(item,dict): raise ValidationError(f"Knowledge Unit {i} must be an object.")
        uid=normalize_slug(item.get("id"),f"Knowledge Unit {i} id")
        area=normalize_slug(item.get("lifeArea"),f"Knowledge Unit {i} lifeArea")
        if area not in valid: raise ValidationError(f"Knowledge Unit {i} references unknown Life Area: {area}")
        if uid in seen: raise ValidationError(f"Duplicate Knowledge Unit id: {uid}")
        seen.add(uid)
        out.append({"id":uid,"lifeArea":area,"title":require_text(item.get("title"),f"Knowledge Unit {i} title"),"summary":require_text(item.get("summary"),f"Knowledge Unit {i} summary"),"experiences":validate_experiences(item.get("experiences"),i,global_experiences)})
    return out

def render_experiences(items:list[dict[str,str]])->str:
    if not items: return '        <p class="small-note">More real-life examples will be added as German Buzz develops.</p>'
    lis="\n".join(f'          <li><a href="{esc(x["url"])}">{esc(x["issueId"])} · {esc(x["topic"])}</a></li>' for x in items)
    return f'        <p class="small-note">Seen in German Buzz:</p>\n        <ul class="life-area-experiences">\n{lis}\n        </ul>'

def render_unit(u:dict[str,Any])->str:
    return f'''      <article class="notice-card" id="{esc(u["id"])}">
        <h3>{esc(u["title"])}</h3>
        <p>{esc(u["summary"])}</p>
{render_experiences(u["experiences"])}
      </article>'''

def render_page(area:dict[str,str],units:list[dict[str,Any]])->str:
    au=[u for u in units if u["lifeArea"]==area["id"]]
    if au:
        units_html="\n".join(render_unit(u) for u in au)
        count=sum(len(u["experiences"]) for u in au)
        intro=("1 German Buzz experience currently contributes to this Life Area." if count==1 else f"{count} German Buzz experiences currently contribute to this Life Area.")
    else:
        units_html='''      <article class="notice-card">
        <p>No Knowledge Units have been added yet. This area will grow from real German Buzz experiences.</p>
      </article>'''
        intro="No experiences have been added yet. Weekly topics will gradually enrich this Life Area."
    canonical=f"{SITE_URL}/mygermanfreund/life-areas/{area['id']}/"
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(area['title'])} | Life Areas | MyGermanFreund</title>
  <meta name="description" content="{esc(area['description'])}">
  <link rel="canonical" href="{canonical}">
  <meta name="robots" content="index,follow">
  <link rel="icon" href="../../../assets/athirikya-logo.png?v=6" type="image/png">
  <link rel="stylesheet" href="../../../styles.css">
  <link rel="stylesheet" href="../../../soothing.css">
  <link rel="stylesheet" href="../../../seo-content.css">
  <link rel="stylesheet" href="../../../humanized.css">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="../../../index.html" aria-label="Athirikya home"><img src="../../../assets/athirikya-logo.png" alt="Athirikya"></a>
    <nav class="nav" aria-label="Main navigation"><a href="../../../index.html">Home</a><a href="../../german-buzz/">German Buzz</a><a href="../../../mygermanfreund.html">MyGermanFreund</a></nav>
  </header>
  <main class="content-page">
    <nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../../../index.html">Athirikya</a> / <a href="../../../mygermanfreund.html">MyGermanFreund</a> / Life Areas / {esc(area['title'])}</nav>
    <article>
      <header class="content-hero"><p class="eyebrow">Life Area</p><h1>{esc(area['title'])}</h1><p class="content-lead">{esc(area['description'])}</p></header>
      <section class="guide-section" aria-labelledby="knowledge-units">
        <h2 id="knowledge-units">Knowledge Units</h2>
        <div class="guide-grid">
{units_html}
        </div>
      </section>
      <section class="guide-section notice-card" aria-labelledby="buzz-experiences"><h2 id="buzz-experiences">German Buzz Experiences</h2><p>{esc(intro)}</p></section>
      <section class="guide-section notice-card"><h2>Related Letter Types</h2><p>Coming soon.</p></section>
      <section class="guide-section notice-card"><h2>Related Did You Know?</h2><p>Coming soon.</p></section>
      <section class="guide-section notice-card"><h2>Official Resources</h2><p>Coming soon.</p></section>
    </article>
  </main>
  <footer class="site-footer"><div><img src="../../../assets/athirikya-logo.png" alt="Athirikya"></div><nav aria-label="Footer navigation"><a href="../../../privacy.html">Privacy</a><a href="../../../terms.html">Terms</a><a href="../../../impressum.html">Impressum</a><a href="../../../contact.html">Contact</a></nav><p>© 2026 Athirikya. All rights reserved.</p></footer>
</body>
</html>
'''

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",type=Path,default=Path.cwd())
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    try:
        root=args.repo_root.resolve()
        areas=validate_life_areas(load_json(LIFE_AREAS_FILE))
        units=validate_knowledge_units(load_json(KNOWLEDGE_UNITS_FILE),{a["id"] for a in areas})
        for area in areas:
            path=root/OUTPUT_ROOT/area["id"]/"index.html"
            print(f"{'WOULD WRITE' if args.dry_run else 'WRITE'}: {path}")
            if not args.dry_run:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(render_page(area,units),encoding="utf-8")
        print(f"Life Areas processed: {len(areas)}"); return 0
    except (OSError,json.JSONDecodeError,ValidationError) as exc:
        print(f"ERROR: {exc}"); return 1
if __name__=="__main__": raise SystemExit(main())
