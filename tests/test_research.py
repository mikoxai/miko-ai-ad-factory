import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("research",Path(__file__).resolve().parents[1]/"scripts/research.py")
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)


def packet():
    p={"product":"Fixture bottle", "website":"https://example.com/product", "market":"US",
       "tracks":{}, "sources":[], "findings":[], "angles":[], "selected_angle_id":"a1"}
    for t in r.TRACKS:
        u="https://example.com/"+t
        p["tracks"][t]={"status":"completed", "method":"synthetic offline fixture", "attempts":[{"url":u,"query":"fixture","at":"2026-09-13T12:00:00Z"}],"notes":""}
        details={"advertiser":"Example","market":"US","filters":"all ads","creative_access":"preview only"} if t=="meta" else {"record_type":"comment","subreddit":"example"} if t=="reddit" else {}
        p["sources"].append({"id":t,"track":t,"url":u,"title":"Fixture","retrieved_at":"2026-09-13T12:00:00Z","observation":"Synthetic evidence, not real research.","inspected":True,"details":details})
    p["findings"]=[{"id":"f1","kind":"interpretation","statement":"Example hypothesis","source_ids":["reddit"]}]
    p["angles"]=[{"id":"a1","hook":"Example hook","rationale":"Example rationale","reference_fit":"Match demonstration beat","proof_or_demo":"Show real product","claim_boundary":"No invented promise","finding_ids":["f1"]}]
    return p


class ResearchTests(unittest.TestCase):
    def test_complete_packet_reports(self):
        with tempfile.TemporaryDirectory() as d:
            result=r.report(packet(),Path(d)/"report")
            self.assertEqual(result["status"],"complete")
            self.assertIn("https://example.com/reddit",Path(result["report"]).read_text())

    def test_init_is_not_research(self):
        with tempfile.TemporaryDirectory() as d:
            result=r.init("A & B","https://example.com","US",[],Path(d)/"research")
            self.assertEqual(result["status"],"planned_not_researched")

    def test_pending_track_blocks(self):
        p=packet(); p["tracks"]["reddit"]["status"]="pending"
        with self.assertRaises(ValueError):r.validate(p)

    def test_missing_reddit_blocks(self):
        p=packet(); del p["tracks"]["reddit"]
        with self.assertRaises(ValueError):r.validate(p)

    def test_titles_alone_not_complete_reddit(self):
        p=packet(); p["sources"][-1]["details"]["record_type"]="thread"
        with self.assertRaises(ValueError):r.validate(p)

    def test_broken_citation_blocks(self):
        p=packet();p["findings"][0]["source_ids"]=["invented"]
        with self.assertRaises(ValueError):r.validate(p)

    def test_blocked_source_needs_acceptance(self):
        p=packet();p["tracks"]["meta"].update(status="blocked",notes="Fixture login required")
        with self.assertRaises(ValueError):r.validate(p)
        p.update(limited_research_approved=True,limited_approval_note="User accepted the disclosed fixture gap.")
        self.assertEqual(r.validate(p)["status"],"limited_approved")

    def test_dedup_keeps_evidence_ids_but_counts_unique_urls(self):
        p=packet();s=copy.deepcopy(p["sources"][0]);s["id"]="brand2";s["url"]+="?utm_source=test";p["sources"].append(s)
        self.assertEqual(r.validate(p)["source_counts"]["brand"],1)

    def test_no_uninspected_sources(self):
        p=packet();p["sources"][0]["inspected"]=False
        with self.assertRaises(ValueError):r.validate(p)


if __name__=="__main__":unittest.main()
