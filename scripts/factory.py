"""Local helpers. No secret command arguments; no automatic paid submissions."""
import argparse
import base64
import hashlib
import hmac
import importlib
import ipaddress
import json
import mimetypes
import math
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "miko-ai-ad-factory"
ACCOUNT = "kie-api"
SEEDANCE = "bytedance/seedance-2-5"
NANO = "nano-banana-pro"
NO_CAPTIONS = "No subtitles, no captions, no transcript text, no added lower thirds or dialogue overlays."


class FactoryError(Exception):
    pass


def credential_backend(platform=None):
    platform = sys.platform if platform is None else platform
    return {"darwin": ("macOS", "Keyring"), "win32": ("Windows", "WinVaultKeyring"),
            "linux": ("SecretService", "Keyring")}.get(platform)


def vault():
    backend = credential_backend()
    if backend is None:
        raise FactoryError("Secure credential storage is unavailable on this platform. No plaintext fallback is used.")
    try:
        module = importlib.import_module("keyring.backends." + backend[0])
        store = getattr(module, backend[1])()
        if store.priority <= 0:
            raise RuntimeError()
        return store
    except Exception:
        raise FactoryError("Secure credential storage is unavailable. Enable your system credential store; Linux requires an unlocked Secret Service and desktop D-Bus session.") from None


def api_key():
    try:
        key = vault().get_password(SERVICE, ACCOUNT)
    except FactoryError:
        raise
    except Exception:
        raise FactoryError("Unable to access secure credential storage. Unlock it and allow access, then try again.") from None
    if not key:
        raise FactoryError("Connect Kie using the local setup screen first.")
    return key


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FactoryError("Provider redirect blocked; verify the documented endpoint.")


def request(path, payload=None, key=None):
    # Deliberately no arbitrary host/base URL or credential-bearing debug output.
    if not (path.startswith("/api/v1/") or path == "/api/file-base64-upload" or
            path == "/gemini/v1/models/gemini-3-8-flash:streamGenerateContent"):
        raise FactoryError("Unsupported API route.")
    secret = key if key is not None else api_key()
    req = urllib.request.Request("https://api.kie.ai" + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + secret, "Content-Type": "application/json"})
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=60) as response:
            raw = response.read(24 * 1024 * 1024).decode()
            # Redact even if a faulty provider echoes the credential.
            raw = raw.replace(secret, "[REDACTED]")
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                chunks = []
                for line in raw.splitlines():
                    if line.startswith("data:") and line[5:].strip() not in ("", "[DONE]"):
                        chunks.append(json.loads(line[5:]))
                data = chunks
            else:
                data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise FactoryError(f"Kie HTTP {exc.code}; no response body logged.") from None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        raise FactoryError("Kie response unavailable or invalid; do not retry a paid submission automatically.") from None
    if isinstance(data, dict) and (data.get("code", 200) != 200 or data.get("success") is False or "error" in data):
        raise FactoryError(f"Kie rejected request (code {data.get('code', 'unknown')}); details redacted.")
    return data


def check(key=None):
    data = request("/api/v1/chat/credit", key=key)
    if not isinstance(data, dict) or not isinstance(data.get("data"), (int, float)):
        raise FactoryError("Unexpected credit-check response; connection not verified.")
    return {"kie": "connected", "credits": data["data"], "models": "not live-tested by this check"}


def json_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Artifacts contain prompts/media URLs, never keys. Still keep them private.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(value, f, indent=2)


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                             "-of", "json", str(Path(path).resolve())], capture_output=True, text=True)
    if result.returncode:
        raise FactoryError("FFprobe could not read that media file.")
    return json.loads(result.stdout)


def evidence(path, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    meta = probe(path)
    json_write(out / "probe.json", meta)
    # Sampling covers full duration; timestamp is derived from filenames/index.
    args = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(Path(path).resolve()),
            "-vf", "fps=1/2,scale=360:-2", "-q:v", "3", str(out / "sample-%05d.jpg")]
    subprocess.run(args, check=True, capture_output=True)
    result = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-i", str(Path(path).resolve()),
        "-vf", "select=gt(scene\\,0.15),showinfo", "-an", "-f", "null", "-"], capture_output=True, text=True)
    import re
    cuts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", result.stderr)]
    json_write(out / "evidence.json", {"duration": meta["format"].get("duration"),
        "sampling_interval_seconds": 2, "timing_precision": "approximate sampling; inspect source for exact boundaries",
        "candidate_cuts": cuts, "cut_scan_succeeded": result.returncode == 0,
        "instruction": "Inspect full sequence and denser windows around cuts/gestures. FFmpeg does not interpret images."})
    return {"evidence_directory": str(out.resolve()), "candidate_cuts": len(cuts)}


def public_media_url(value):
    if not isinstance(value, str):
        raise FactoryError("Media references must be HTTPS URLs.")
    u = urllib.parse.urlsplit(value)
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.fragment:
        raise FactoryError("Use HTTPS media URLs without credentials or fragments.")
    if u.hostname.lower() == "localhost" or u.hostname.endswith((".local", ".internal")):
        raise FactoryError("Private media addresses are not accepted.")
    try:
        if not ipaddress.ip_address(u.hostname).is_global:
            raise FactoryError("Private media addresses are not accepted.")
    except ValueError:
        pass


def validate_job(job):
    if set(job) != {"model", "input"} or job["model"] not in (SEEDANCE, NANO):
        raise FactoryError("Use only model/input with Seedance 2.5 or Nano Banana Pro.")
    x = job["input"]
    if not isinstance(x, dict) or not isinstance(x.get("prompt"), str) or not x["prompt"].strip():
        raise FactoryError("A nonempty prompt is required.")
    if job["model"] == SEEDANCE:
        allowed = {"prompt", "first_frame_url", "last_frame_url", "reference_image_urls",
            "reference_video_urls", "reference_audio_urls", "generate_audio", "return_last_frame",
            "resolution", "aspect_ratio", "duration", "output_format", "web_search", "nsfw_checker"}
        if set(x) - allowed:
            raise FactoryError("Unknown Seedance fields; no invented extension endpoint.")
        if len(x["prompt"]) > 30000 or NO_CAPTIONS not in x["prompt"]:
            raise FactoryError("Seedance prompt must fit 30,000 characters and include the exact no-captions sentence.")
        if type(x.get("duration")) is not int or not 4 <= x["duration"] <= 30:
            raise FactoryError("Use an explicit Seedance duration of 4–30 seconds.")
        if x.get("resolution") not in ("480p", "720p", "1080p"):
            raise FactoryError("Seedance API resolutions are 480p/720p/1080p; do not assume 4K.")
        if x.get("aspect_ratio") not in ("16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "adaptive"):
            raise FactoryError("Unsupported aspect ratio.")
        for k in ("generate_audio", "return_last_frame", "web_search", "nsfw_checker"):
            if k in x and type(x[k]) is not bool:
                raise FactoryError("Boolean settings must be true or false.")
        if x.get("nsfw_checker") is not True:
            raise FactoryError("This kit keeps the provider safety checker enabled.")
        if x.get("output_format", "mp4") not in ("mp4", "mov"):
            raise FactoryError("Unsupported output format.")
        refs = ("reference_image_urls", "reference_video_urls", "reference_audio_urls")
        if (x.get("first_frame_url") or x.get("last_frame_url")) and any(x.get(k) for k in refs):
            raise FactoryError("First/last-frame and multimodal reference modes cannot be combined.")
        if x.get("last_frame_url") and not x.get("first_frame_url"):
            raise FactoryError("Last frame requires first frame.")
        limits = {"reference_image_urls": 30, "reference_video_urls": 10, "reference_audio_urls": 10}
    else:
        if set(x) - {"prompt", "image_input", "aspect_ratio", "resolution", "output_format"}:
            raise FactoryError("Unknown Nano Banana Pro input field.")
        if len(x["prompt"]) > 10000 or x.get("resolution") not in ("1K", "2K", "4K"):
            raise FactoryError("Nano Banana Pro needs <=10,000 characters and 1K/2K/4K resolution.")
        if x.get("aspect_ratio") not in ("1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9", "auto"):
            raise FactoryError("Unsupported Nano Banana Pro aspect ratio.")
        if x.get("output_format", "png") not in ("png", "jpg"):
            raise FactoryError("Unsupported image output format.")
        limits = {"image_input": 8}
    for k, limit in limits.items():
        values = x.get(k, [])
        if not isinstance(values, list) or len(values) > limit:
            raise FactoryError(f"Invalid {k} count.")
        for value in values:
            public_media_url(value)
    for k in ("first_frame_url", "last_frame_url"):
        if x.get(k):
            public_media_url(x[k])


def validate_media(job, media):
    """Local evidence manifest associates each remote reference with its local file."""
    if not isinstance(media, list):
        raise FactoryError("media must be a list.")
    index = {m["url"]: m for m in media}
    x = job["input"]
    keys = ["reference_image_urls", "reference_video_urls", "reference_audio_urls", "image_input"]
    all_urls = [u for k in keys for u in x.get(k, [])]
    all_urls += [x[k] for k in ("first_frame_url", "last_frame_url") if x.get(k)]
    totals = {"video": 0.0, "audio": 0.0}
    fingerprints = {}
    for url in all_urls:
        if url not in index:
            raise FactoryError("Every reference needs its local media manifest entry.")
        m = index[url]
        if m.get("role") not in ("product", "graphic", "voice", "motion_excerpt", "continuation"):
            raise FactoryError("Reference role not approved for this text-character workflow.")
        p = Path(m["path"]).resolve()
        expected = "audio" if url in x.get("reference_audio_urls", []) else "video" if url in x.get("reference_video_urls", []) else "image"
        if m["role"] == "voice" and expected != "audio":
            raise FactoryError("Voice assets must be audio references.")
        if m.get("rights_confirmed") is not True:
            raise FactoryError("Reference rights/upload approval not recorded.")
        meta = probe(p)
        fingerprints[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        if expected in totals:
            d = float(meta["format"]["duration"])
            if not 2 <= d <= 30:
                raise FactoryError("Audio/video reference duration must be 2–30 seconds.")
            totals[expected] += d
            limit_mb = 15 if expected == "audio" else 200
            if expected == "audio" and not any(s["codec_type"] == "audio" for s in meta["streams"]):
                raise FactoryError("Audio reference has no audio stream.")
            if expected == "video":
                streams = [s for s in meta["streams"] if s["codec_type"] == "video"]
                if not streams:
                    raise FactoryError("Video reference has no video stream.")
                v = streams[0]; w, h = v["width"], v["height"]
                a, b = v["avg_frame_rate"].split("/"); fps = float(a) / float(b)
                if not (300 <= min(w, h) and max(w, h) <= 6000 and .4 <= w/h <= 2.5 and
                        409600 <= w*h <= 927408 and 24 <= fps <= 60):
                    raise FactoryError("Normalize the video reference to documented dimensions/pixels/FPS before upload.")
        else:
            limit_mb = 30
            if not any(s["codec_type"] == "video" for s in meta["streams"]):
                raise FactoryError("Image reference is not readable as an image.")
        if p.stat().st_size > limit_mb * 1024 * 1024:
            raise FactoryError("Reference file exceeds provider size limit.")
    if any(d > 30.001 for d in totals.values()):
        raise FactoryError("Combined reference video/audio duration exceeds 30 seconds for its type.")
    return fingerprints, totals


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def database(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    db = sqlite3.connect(directory / "plans.sqlite3", timeout=5)
    os.chmod(directory / "plans.sqlite3", 0o600)
    db.execute("CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, body TEXT, state TEXT, created REAL, task TEXT)")
    return db


def prepare(packet, directory):
    if set(packet) - {"job", "media", "approved_budget_usd", "estimated_cost_usd", "cost_note", "storyboard_approved"}:
        raise FactoryError("Unknown packet fields.")
    job = packet["job"]; validate_job(job)
    if packet.get("storyboard_approved") is not True:
        raise FactoryError("Approve the storyboard first.")
    budget = packet.get("approved_budget_usd")
    if type(budget) not in (int, float) or not math.isfinite(budget) or not 0 < budget < 10000:
        raise FactoryError("Record the user-approved maximum USD budget for this job.")
    estimate = packet.get("estimated_cost_usd")
    if type(estimate) not in (int, float) or not math.isfinite(estimate) or not 0 < estimate <= budget:
        raise FactoryError("A current positive cost estimate within the approved budget is required; unknown/over-budget jobs stop.")
    if not isinstance(packet.get("cost_note"), str) or not packet["cost_note"].strip():
        raise FactoryError("Record current price evidence or explain unknown pricing for review.")
    fingerprints, totals = validate_media(job, packet.get("media", []))
    body = {"packet": packet, "local_fingerprints": fingerprints, "reference_seconds": totals}
    plan = secrets.token_hex(12)
    with database(directory) as db:
        db.execute("INSERT INTO plans VALUES (?,?,?,?,NULL)", (plan, json.dumps(body), "prepared", time.time()))
    return {"plan_id": plan, "state": "prepared", "request_sha256": digest(body), "review": body,
            "warning": "No provider task created. Budget is a user approval ceiling, not a provider-enforced cap. Verify quote before submitting."}


def submit(plan, approval, directory):
    if not hmac.compare_digest(plan, approval or ""):
        raise FactoryError("Explicit approval ID must match the plan ID.")
    db = database(directory)
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT body,state,created FROM plans WHERE id=?", (plan,)).fetchone()
        if not row or row[1] != "prepared" or time.time() - row[2] > 1800:
            raise FactoryError("Plan unavailable, expired or already submitted. Do not resubmit ambiguous jobs.")
        body = json.loads(row[0]); packet = body["packet"]
        validate_job(packet["job"])
        current, _ = validate_media(packet["job"], packet.get("media", []))
        if current != body["local_fingerprints"]:
            raise FactoryError("Reference changed since planning; create and approve a new plan.")
        db.execute("UPDATE plans SET state='submitting' WHERE id=?", (plan,)); db.commit()
        try:
            result = request("/api/v1/jobs/createTask", packet["job"])
            task = result.get("data", {}).get("taskId")
            if not task or not isinstance(task, str):
                raise FactoryError("No task ID returned; inspect Kie history before any new submission.")
        except Exception:
            db.execute("UPDATE plans SET state='unknown' WHERE id=?", (plan,)); db.commit()
            raise
        db.execute("UPDATE plans SET state='submitted',task=? WHERE id=?", (task, plan)); db.commit()
        return {"plan_id": plan, "task_id": task, "state": "submitted"}
    finally:
        db.close()


def upload(path):
    p = Path(path).resolve()
    if not p.is_file() or p.stat().st_size > 20 * 1024 * 1024:
        raise FactoryError("This conservative Base64 upload helper accepts local files up to 20MiB. Compress/chunk larger media or use a verified streaming uploader.")
    mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    if not mime.startswith(("image/", "video/", "audio/")):
        raise FactoryError("Only explicit image/video/audio files may be uploaded.")
    return request("/api/file-base64-upload", {"base64Data": "data:"+mime+";base64,"+base64.b64encode(p.read_bytes()).decode(),
        "uploadPath": "miko-ad-factory", "fileName": secrets.token_hex(12)+p.suffix.lower()})


def analyze(path, prompt):
    p = Path(path).resolve()
    if p.stat().st_size > 18 * 1024 * 1024:
        raise FactoryError("Inline analysis fixture limited to 18MiB; compress/segment with complete timecode coverage.")
    mime = mimetypes.guess_type(p.name)[0] or "video/mp4"
    if not mime.startswith(("video/", "image/", "audio/")):
        raise FactoryError("Analysis requires media.")
    # Standard Gemini multimodal shape; Kie media passthrough needs live acceptance test.
    return request("/gemini/v1/models/gemini-3-8-flash:streamGenerateContent", {
        "contents": [{"role": "user", "parts": [{"text": Path(prompt).read_text()},
        {"inlineData": {"mimeType": mime, "data": base64.b64encode(p.read_bytes()).decode()}}]}]})


def make_server(store=None, checker=check):
    token = secrets.token_urlsafe(24)
    state = {"kie": "waiting", "models": "unverified"}
    save = store or (lambda value: vault().set_password(SERVICE, ACCOUNT, value))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body, kind="application/json"):
            raw = (json.dumps(body) if kind == "application/json" else body).encode()
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers(); self.wfile.write(raw)

        def allowed(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.allowed():
                return self.send(403, {"error": "Invalid host"})
            if self.path == "/" + token + "/status":
                return self.send(200, dict(state))
            if self.path != "/" + token:
                return self.send(404, {"error": "Not found"})
            html = (ROOT / "setup.html").read_text().replace("__TOKEN__", token)
            return self.send(200, html, "text/html; charset=utf-8")

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (not self.allowed() or self.path != "/"+token+"/connect" or
                self.headers.get("Origin") != origin or
                self.headers.get("X-Setup-Token") != token or
                self.headers.get("Content-Type") != "application/json"):
                return self.send(403, {"error": "Invalid session or origin"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    raise ValueError()
                body = json.loads(self.rfile.read(size))
                key = body.get("key", "")
                if not isinstance(key, str) or not 8 <= len(key) <= 2048 or any(c.isspace() for c in key):
                    raise ValueError()
                result = checker(key)
                save(key)
                key = None; body.clear()
                state.update(result)
                self.send(200, dict(state))
                print(json.dumps({"event": "kie_connected", "next": "connect_whop_in_chat"}), flush=True)
            except Exception:
                state["kie"] = "connection_failed"
                self.send(400, {"error": "Check your API key and allow access to your system credential store. Linux requires an unlocked Secret Service and desktop D-Bus session."})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    return server, f"http://127.0.0.1:{server.server_port}/{token}"


def main():
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state-dir", default=str(ROOT / "runtime"))
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("setup"); sub.add_parser("check"); sub.add_parser("doctor")
    s = sub.add_parser("status"); s.add_argument("--setup-url", required=True)
    s = sub.add_parser("evidence"); s.add_argument("file"); s.add_argument("--out", required=True)
    s = sub.add_parser("upload"); s.add_argument("file"); s.add_argument("--approve-upload", action="store_true")
    s = sub.add_parser("analyze"); s.add_argument("file"); s.add_argument("--prompt", required=True); s.add_argument("--out", required=True); s.add_argument("--approve-paid-analysis", action="store_true")
    s = sub.add_parser("prepare"); s.add_argument("packet")
    s = sub.add_parser("submit"); s.add_argument("plan"); s.add_argument("--approve", required=True)
    s = sub.add_parser("task"); s.add_argument("id")
    args = p.parse_args()
    try:
        if args.command == "setup":
            server, url = make_server()
            print(json.dumps({"setup_url": url, "expires_seconds": 900, "note": "Enter key only in browser. Whop connects separately in chat."}), flush=True)
            timer = threading.Timer(900, server.shutdown); timer.daemon = True; timer.start()
            try:
                server.serve_forever()
            finally:
                server.server_close(); timer.cancel()
            return
        if args.command == "doctor":
            result = {"python": sys.version.split()[0], "platform": sys.platform,
                "ffmpeg": bool(shutil.which("ffmpeg")), "ffprobe": bool(shutil.which("ffprobe")),
                "credential_backend": credential_backend()[0] if credential_backend() else "unsupported",
                "credential_backend_status": "configured; availability and access checked during connection",
                "whop": "discover and verify native host tools", "paid_provider_tests": "not performed"}
        elif args.command == "check":
            result = check()
        elif args.command == "status":
            u = urllib.parse.urlsplit(args.setup_url)
            if u.scheme != "http" or u.hostname != "127.0.0.1" or not u.port or u.username or u.query or u.fragment:
                raise FactoryError("Use the exact loopback setup URL.")
            with urllib.request.build_opener(NoRedirect).open(args.setup_url+"/status", timeout=5) as r:
                result = json.load(r)
        elif args.command == "evidence":
            result = evidence(args.file, args.out)
        elif args.command == "upload":
            if not args.approve_upload:
                raise FactoryError("Upload requires explicit user permission and --approve-upload.")
            result = upload(args.file)
        elif args.command == "analyze":
            if not args.approve_paid_analysis:
                raise FactoryError("Analysis sends media to Kie and may cost credits; approval required.")
            result = analyze(args.file, args.prompt)
            json_write(args.out, result); result = {"analysis_output": str(Path(args.out).resolve())}
        elif args.command == "prepare":
            result = prepare(json.loads(Path(args.packet).read_text()), args.state_dir)
        elif args.command == "submit":
            result = submit(args.plan, args.approve, args.state_dir)
        elif args.command == "task":
            result = request("/api/v1/jobs/recordInfo?"+urllib.parse.urlencode({"taskId": args.id}))
        print(json.dumps(result, indent=2))
    except FactoryError as exc:
        print(json.dumps({"error": str(exc)})); sys.exit(1)
    except Exception:
        print(json.dumps({"error": "Operation failed; sensitive exception details suppressed."})); sys.exit(1)


if __name__ == "__main__":
    main()
