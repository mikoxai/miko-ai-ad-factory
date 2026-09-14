import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("factory", ROOT / "scripts/factory.py")
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)


def packet():
    return {"job": {"model": f.SEEDANCE, "input": {"prompt": "An original two-person conversation. " + f.NO_CAPTIONS,
        "duration": 5, "resolution": "720p", "aspect_ratio": "9:16", "nsfw_checker": True,
        "generate_audio": True}}, "media": [], "storyboard_approved": True,
        "approved_budget_usd": 3, "estimated_cost_usd": 1.575, "cost_note": "Synthetic offline test quote; not real provider pricing."}


class Validation(unittest.TestCase):
    def test_exact_model_and_caption_rule(self):
        p = packet(); f.validate_job(p["job"])
        p["job"]["input"]["prompt"] = "Add captions"
        with self.assertRaises(f.FactoryError): f.validate_job(p["job"])
        p = packet(); p["job"]["model"] = "other-model"
        with self.assertRaises(f.FactoryError): f.validate_job(p["job"])

    def test_mutually_exclusive_modes(self):
        p = packet(); p["job"]["input"].update(first_frame_url="https://example.com/a.png", reference_audio_urls=["https://example.com/a.wav"])
        with self.assertRaises(f.FactoryError): f.validate_job(p["job"])

    def test_invalid_resolution_duration_checker(self):
        for key, value in [("resolution", "4K"), ("duration", 31), ("duration", True), ("nsfw_checker", False)]:
            p = packet(); p["job"]["input"][key] = value
            with self.assertRaises(f.FactoryError): f.validate_job(p["job"])

    def test_reference_counts_and_urls(self):
        p = packet(); p["job"]["input"]["reference_image_urls"] = ["https://example.com/a.png"] * 31
        with self.assertRaises(f.FactoryError): f.validate_job(p["job"])
        for url in ["http://example.com/a.png", "https://localhost/a", "https://127.0.0.1/a", "https://user:pass@example.com/a"]:
            with self.assertRaises(f.FactoryError): f.public_media_url(url)

    def test_nano_pro_not_two(self):
        f.validate_job({"model": f.NANO, "input": {"prompt": "Editorial card", "resolution": "2K", "aspect_ratio": "9:16", "image_input": []}})

    def test_missing_manifest(self):
        p = packet(); p["job"]["input"]["reference_audio_urls"] = ["https://example.com/a.wav"]
        with self.assertRaises(f.FactoryError): f.validate_media(p["job"], [])

    def test_combined_audio_duration(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"a.wav"; path.write_bytes(b"fixture")
            urls = ["https://example.com/a.wav", "https://example.com/b.wav"]
            p = packet(); p["job"]["input"]["reference_audio_urls"] = urls
            media = [{"url": u, "path": str(path), "role": "voice", "rights_confirmed": True} for u in urls]
            with patch.object(f, "probe", return_value={"format": {"duration": "16"}, "streams": [{"codec_type": "audio"}]}):
                with self.assertRaises(f.FactoryError): f.validate_media(p["job"], media)


class Plans(unittest.TestCase):
    def test_budget_is_checked_before_provider(self):
        with tempfile.TemporaryDirectory() as d, patch.object(f, "request") as req:
            for value in [None, 4, -1, float("nan"), float("inf")]:
                p = packet(); p["estimated_cost_usd"] = value
                with self.assertRaises(f.FactoryError): f.prepare(p, d)
            req.assert_not_called()

    def test_prepare_is_offline_and_submission_is_once(self):
        with tempfile.TemporaryDirectory() as d, patch.object(f, "request", return_value={"data": {"taskId": "test-task"}}) as req:
            plan = f.prepare(packet(), d)["plan_id"]; req.assert_not_called()
            with self.assertRaises(f.FactoryError): f.submit(plan, "wrong", d)
            req.assert_not_called()
            self.assertEqual(f.submit(plan, plan, d)["task_id"], "test-task")
            with self.assertRaises(f.FactoryError): f.submit(plan, plan, d)
            self.assertEqual(req.call_count, 1)

    def test_timeout_is_not_retried(self):
        with tempfile.TemporaryDirectory() as d, patch.object(f, "request", side_effect=f.FactoryError("timeout")) as req:
            plan = f.prepare(packet(), d)["plan_id"]
            with self.assertRaises(f.FactoryError): f.submit(plan, plan, d)
            with self.assertRaises(f.FactoryError): f.submit(plan, plan, d)
            self.assertEqual(req.call_count, 1)

    def test_expiry(self):
        with tempfile.TemporaryDirectory() as d, patch.object(f, "request") as req:
            plan = f.prepare(packet(), d)["plan_id"]
            with f.database(d) as db: db.execute("UPDATE plans SET created=0 WHERE id=?", (plan,))
            with self.assertRaises(f.FactoryError): f.submit(plan, plan, d)
            req.assert_not_called()

    def test_missing_task_id_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as d, patch.object(f, "request", return_value={"code": 200, "data": {}}) as req:
            plan = f.prepare(packet(), d)["plan_id"]
            with self.assertRaises(f.FactoryError): f.submit(plan, plan, d)
            with self.assertRaises(f.FactoryError): f.submit(plan, plan, d)
            self.assertEqual(req.call_count, 1)


class CredentialStores(unittest.TestCase):
    def test_platform_routes(self):
        for platform, backend in [("darwin", ("macOS", "Keyring")), ("win32", ("Windows", "WinVaultKeyring")), ("linux", ("SecretService", "Keyring"))]:
            with self.subTest(platform=platform):
                self.assertEqual(f.credential_backend(platform), backend)
                with patch.object(f.sys, "platform", platform), patch.object(f.importlib, "import_module") as load:
                    store = getattr(load.return_value, backend[1]).return_value
                    store.priority = 5
                    self.assertIs(f.vault(), store)
                    load.assert_called_once_with("keyring.backends." + backend[0])

    def test_no_insecure_fallback(self):
        with patch.object(f.sys, "platform", "unknown"), patch.object(f.importlib, "import_module") as load:
            with self.assertRaises(f.FactoryError): f.vault()
            load.assert_not_called()
        with patch.object(f.sys, "platform", "linux"), patch.object(f.importlib, "import_module", side_effect=RuntimeError("private details")):
            with self.assertRaises(f.FactoryError) as ctx: f.vault()
            self.assertNotIn("private details", str(ctx.exception))

    def test_storage_errors_redacted(self):
        with patch.object(f, "vault") as store:
            store.return_value.get_password.side_effect = RuntimeError("private details")
            with self.assertRaises(f.FactoryError) as ctx: f.api_key()
            self.assertNotIn("private details", str(ctx.exception))


class Setup(unittest.TestCase):
    def setUp(self):
        self.saved = []
        self.server, self.url = f.make_server(store=self.saved.append, checker=lambda key: {"kie": "connected"})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def post(self, origin=None, host=None):
        parsed = urllib.parse.urlsplit(self.url)
        headers = {"Content-Type": "application/json", "X-Setup-Token": parsed.path[1:]}
        if origin: headers["Origin"] = origin
        if host: headers["Host"] = host
        req = urllib.request.Request(self.url+"/connect", data=json.dumps({"key": "TEST_ONLY_NOT_A_REAL_KEY"}).encode(), headers=headers)
        return urllib.request.urlopen(req)

    def test_connect_returns_status_not_key(self):
        origin = self.url.rsplit("/", 1)[0]
        with self.post(origin) as response: raw = response.read().decode()
        self.assertNotIn("TEST_ONLY", raw)
        self.assertEqual(self.saved, ["TEST_ONLY_NOT_A_REAL_KEY"])
        with urllib.request.urlopen(self.url+"/status") as response:
            self.assertEqual(json.load(response)["kie"], "connected")

    def test_cross_origin_and_host_rejected(self):
        for origin, host in [(None,None), ("https://evil.example",None), (self.url.rsplit("/",1)[0],"evil.example")]:
            with self.assertRaises(urllib.error.HTTPError) as ctx: self.post(origin,host)
            self.assertEqual(ctx.exception.code,403)
        self.assertEqual(self.saved,[])

    def test_html_does_not_store_keys_in_browser(self):
        with urllib.request.urlopen(self.url) as response:
            text = response.read().decode()
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn('type="password"', text)
        self.assertNotIn("localStorage", text)
        self.assertNotIn("sessionStorage", text)


if __name__ == "__main__": unittest.main()
