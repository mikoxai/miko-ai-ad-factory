"""Plan browser research and validate source-backed handoffs. Not a network scraper."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.parse

TRACKS = ("brand", "google", "meta", "google_ads", "reddit")
STATUSES = ("pending", "completed", "partial", "blocked", "no_results")


def now():
    return datetime.now(timezone.utc).isoformat()


def url(value):
    u = urllib.parse.urlsplit(value)
    if u.scheme not in ("https", "http") or not u.hostname or u.username or u.password:
        raise ValueError("Evidence needs a public web URL without embedded credentials.")
    return value


def canonical(value):
    u = urllib.parse.urlsplit(url(value))
    query = [(k,v) for k,v in urllib.parse.parse_qsl(u.query) if not k.startswith("utm_") and k not in ("fbclid", "gclid")]
    return urllib.parse.urlunsplit((u.scheme, u.netloc.lower(), u.path.rstrip("/"), urllib.parse.urlencode(query), ""))


def write(path, data):
    with Path(path).open("x") as f:
        json.dump(data, f, indent=2)


def init(product, website, market, competitors, out):
    url(website)
    path = Path(out); path.mkdir(parents=True, exist_ok=False)
    searches = [f'{product} reviews {market}', f'{product} alternatives', f'{product} complaints',
                f'{product} comparison', f'site:reddit.com {product} worth it',
                f'site:reddit.com {product} disappointed', f'site:reddit.com {product} recommendations']
    for competitor in competitors:
        searches.extend([f'{competitor} pricing {market}', f'site:reddit.com {competitor} alternatives'])
    plan = {"product": product, "website": website, "market": market, "created_at": now(),
        "google_queries": [{"query": q, "url": "https://www.google.com/search?"+urllib.parse.urlencode({"q": q})} for q in searches],
        "meta": {"entry_url": "https://www.facebook.com/ads/library/", "searches": [product]+competitors,
                 "instructions": "Use observed UI to select market, All ads and filters. Open ad details and record actual permalinks."},
        "google_ads": {"entry_url": "https://adstransparency.google.com/", "searches": [website]+competitors},
        "reddit": {"entry_url": "https://www.reddit.com/search/", "searches": searches[4:7],
                   "instructions": "Prefer authenticated Reddit MCP; otherwise open actual public threads/comments from search."},
        "note": "Plan only. Agent must browse/extract sources and fill evidence.json. No scraping performed by init."}
    packet = {"product": product, "website": website, "market": market,
        "tracks": {t: {"status": "pending", "method": "", "attempts": [], "notes": ""} for t in TRACKS},
        "sources": [], "findings": [], "angles": [], "selected_angle_id": None,
        "limited_research_approved": False, "limited_approval_note": ""}
    write(path/"query-plan.json", plan); write(path/"evidence.json", packet)
    return {"research_directory": str(path.resolve()), "status": "planned_not_researched"}


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name+" must be nonempty text.")


def validate(packet):
    text(packet.get("product"), "product"); url(packet["website"]); text(packet.get("market"), "market")
    tracks = packet.get("tracks", {})
    if set(tracks) != set(TRACKS):
        raise ValueError("All five research tracks must be present, including Reddit.")
    sources = packet.get("sources", [])
    by_id = {}; counts = {t: set() for t in TRACKS}
    for s in sources:
        text(s.get("id"), "source id")
        if s["id"] in by_id: raise ValueError("Duplicate source ID.")
        if s.get("track") not in TRACKS: raise ValueError("Unknown source track.")
        url(s["url"]); text(s.get("title"), "source title")
        datetime.fromisoformat(s["retrieved_at"].replace("Z", "+00:00"))
        text(s.get("observation"), "source observation")
        if s.get("inspected") is not True: raise ValueError("Sources must be actually inspected, not query plans/snippets.")
        if s["track"] == "meta":
            for key in ("advertiser", "market", "filters", "creative_access"):
                text(s.get("details", {}).get(key), "Meta "+key)
        if s["track"] == "reddit":
            if s.get("details", {}).get("record_type") not in ("thread", "comment"):
                raise ValueError("Reddit evidence must distinguish threads and comments.")
            text(s["details"].get("subreddit"), "subreddit")
        by_id[s["id"]] = s; counts[s["track"]].add(canonical(s["url"]))
    gaps = []
    for track, data in tracks.items():
        status = data.get("status")
        if status not in STATUSES or status == "pending":
            raise ValueError("Every source track must be attempted before research handoff.")
        text(data.get("method"), track+" method")
        attempts = data.get("attempts", [])
        if not attempts: raise ValueError(track+" requires an attempt log.")
        for attempt in attempts:
            url(attempt["url"]); text(attempt.get("query"), "attempt query/action")
            datetime.fromisoformat(attempt["at"].replace("Z", "+00:00"))
        if status == "completed" and not counts[track]:
            raise ValueError(track+" cannot be complete with no inspected evidence.")
        if track == "reddit" and status == "completed" and not any(s["track"] == "reddit" and s["details"]["record_type"] == "comment" for s in sources):
            raise ValueError("Completed Reddit research needs comment evidence, not titles alone.")
        if status != "completed":
            text(data.get("notes"), track+" gap reason"); gaps.append(track)
    if gaps and (packet.get("limited_research_approved") is not True or not packet.get("limited_approval_note", "").strip()):
        raise ValueError("Incomplete coverage requires explicit user acceptance and an approval note.")
    findings = packet.get("findings", []); finding_ids = set()
    for item in findings:
        text(item.get("id"), "finding id"); text(item.get("statement"), "finding statement")
        if item["id"] in finding_ids: raise ValueError("Duplicate finding ID.")
        finding_ids.add(item["id"])
        if item.get("kind") not in ("observed_fact", "attributed_claim", "interpretation"):
            raise ValueError("Findings need fact/claim/interpretation labels.")
        if not item.get("source_ids") or any(s not in by_id for s in item["source_ids"]):
            raise ValueError("Every finding must reference real evidence IDs.")
    if not findings: raise ValueError("Findings are required before creative handoff.")
    angles = packet.get("angles", []); angle_ids = set()
    for item in angles:
        for key in ("id", "hook", "rationale", "reference_fit", "proof_or_demo", "claim_boundary"):
            text(item.get(key), "angle "+key)
        if item["id"] in angle_ids: raise ValueError("Duplicate angle ID.")
        angle_ids.add(item["id"])
        if not item.get("finding_ids") or any(x not in finding_ids for x in item["finding_ids"]):
            raise ValueError("Angles must connect to sourced findings.")
    if packet.get("selected_angle_id") not in angle_ids:
        raise ValueError("Select a researched angle before producing a handoff.")
    return {"schema": "miko-research-handoff/v1", "status": "limited_approved" if gaps else "complete",
        "product": packet["product"], "market": packet["market"], "source_counts": {k:len(v) for k,v in counts.items()},
        "gaps": gaps, "tracks": tracks, "sources": sources, "findings": findings,
        "angles": angles, "selected_angle_id": packet["selected_angle_id"],
        "limited_approval_note": packet.get("limited_approval_note", ""),
        "warning": "Structural validation only; semantic quality, actual inspection and source truth require agent review."}


def report(packet, out):
    handoff = validate(packet)
    path = Path(out); path.mkdir(parents=True, exist_ok=False)
    write(path/"creative-handoff.json", handoff)
    lines = ["# Product and ad research", "", packet["product"], "", "Status: "+handoff["status"], "", "## Coverage", ""]
    for t in TRACKS:
        lines.append(f'- {t}: {packet["tracks"][t]["status"]}; {handoff["source_counts"][t]} distinct source URLs. {packet["tracks"][t].get("notes", "")}')
    lines.extend(["", "## Findings", ""])
    by_id = {s["id"]:s for s in packet["sources"]}
    for item in packet["findings"]:
        cites = ", ".join(f'[{sid}]({by_id[sid]["url"]})' for sid in item["source_ids"])
        lines.append(f'- {item["id"]} ({item["kind"]}): {item["statement"]} Sources: {cites}')
    lines.extend(["", "## Creative angles", ""])
    for item in packet["angles"]:
        lines.extend(["### "+item["id"]+(" · selected" if item["id"]==packet["selected_angle_id"] else ""), "", item["hook"], "",
            "Rationale: "+item["rationale"], "", "Reference fit: "+item["reference_fit"], "",
            "Proof/demo: "+item["proof_or_demo"], "", "Claim boundary: "+item["claim_boundary"], "",
            "Evidence findings: "+", ".join(item["finding_ids"]), ""])
    lines.extend(["## Source ledger", ""])
    for s in packet["sources"]:
        lines.extend([f'### {s["id"]}: {s["title"]}', "", s["url"], "", "Retrieved: "+s["retrieved_at"], "", s["observation"], ""])
    (path/"research-brief.md").write_text("\n".join(lines))
    return {"report": str((path/"research-brief.md").resolve()), "handoff": str((path/"creative-handoff.json").resolve()), "status": handoff["status"]}


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="command",required=True)
    s = sub.add_parser("init"); s.add_argument("--product",required=True); s.add_argument("--url",required=True); s.add_argument("--market",required=True); s.add_argument("--competitor",action="append",default=[]); s.add_argument("--out",required=True)
    s = sub.add_parser("report"); s.add_argument("packet"); s.add_argument("--out",required=True)
    a = p.parse_args()
    try:
        result = init(a.product,a.url,a.market,a.competitor,a.out) if a.command=="init" else report(json.loads(Path(a.packet).read_text()),a.out)
        print(json.dumps(result,indent=2))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        p.exit(1,"Research incomplete or invalid: "+str(exc)+"\n")


if __name__ == "__main__": main()
