# Kie contracts and helper usage

Selected models: analysis `gemini-3-8-flash`; video `bytedance/seedance-2-5`; graphics `nano-banana-pro`. GPT-6 Astra orchestrates in the user's existing host. Do not substitute mis-transcribed version names, image models or providers.

Sources checked September13,2026:
- https://docs.kie.ai/market/bytedance/seedance-2-5
- https://docs.kie.ai/market/google/pro-image-to-image
- https://docs.kie.ai/market/gemini/gemini-3-8-flash
- https://docs.kie.ai/common-api/get-account-credits
- https://docs.kie.ai/file-upload-api/upload-file-base-64
- https://docs.kie.ai/market/common/get-task-detail
- https://kie.ai/seedance-2-5

## Verified schema versus live acceptance

Documents describe `POST https://api.kie.ai/api/v1/jobs/createTask` with `{model,input}` and optional callback; this kit omits callbacks and polls task status. `GET /api/v1/jobs/recordInfo?taskId=...` returns job status. Credit validation uses `GET /api/v1/chat/credit`. Bearer authentication is injected inside the helper from Keychain.

Seedance: explicit4–30s; prompt<=30,000 characters;480p/720p/1080p; native audio; image/video/audio references. First/last-frame mode and reference mode are mutually exclusive; last frame requires first frame. Actual API lists30 images,10 videos,10 audio files, not a guaranteed combined30/50 references. Total video duration<=30s. Audio docs have a copy/paste error mentioning videos; the user's Playground says combined audio<=30s, which the helper conservatively enforces. Individual audio/video samples2–30s. Video reference pixel area409,600–927,408,24–60fps; normalize e.g720×1280 before upload. Preserve output resolution independently. Image30MB,video200MB,audio15MB provider limits; helper uploads are more conservative.

The marketing README mentions4K but the API enum stops at1080p. Do not submit4K or promise it from this adapter. No `omni_reference` switch is necessary here: the reference arrays select multimodal input. No native extend endpoint is assumed; a verified generated clip can serve as a subsequent reference.

Nano Banana Pro: model `nano-banana-pro`, prompt<=10,000, `image_input`<=8, `resolution`1K/2K/4K, PNG/JPG. Only graphics/product imagery, no character generation in this factory.

Gemini: configured route `/gemini/v1/models/gemini-3-8-flash:streamGenerateContent`, `contents` structure. Helper provides standard inlineData media and parses JSON/SSE. This exact payload/auth path requires live verification. Docs mix X-Goog-Api-Key prose with Bearer examples; use documented Bearer example first and stop on auth/media errors rather than silently switching providers. Test a short owned sample before production use. Inline helper limit18MiB is local, not a claimed provider limit. For long sources use compressed video/segments with original timestamps and full coverage.

## Costs

User-supplied September13 rate snapshot in USD/s:

| Resolution | No video reference: output seconds | With video reference: input + output seconds |
|---|---:|---:|
|480p|0.140|0.085|
|720p|0.315|0.190|
|1080p|0.570|0.3425|

Example:30s1080p no-video=$17.10;30s input+30s output at video rate=$20.55. A lower unit rate is not automatically a lower total price. Snapshot is beta pricing with1080 offer expiryOctober17,2026; recheck before quoting. Nano/Gemini costs need current quotes. The helper does not claim to enforce a provider billing cap; record the user's per-job maximum and price evidence before submission, and don't submit if the estimate exceeds it or unknown pricing isn't acceptable to the user. No blind retry.

## Commands (from package root)

```sh
uv run python scripts/factory.py doctor
uv run python scripts/factory.py setup
uv run python scripts/factory.py status --setup-url LOOPBACK_URL
uv run python scripts/factory.py evidence /absolute/reference.mp4 --out /absolute/new-evidence-folder
uv run python scripts/factory.py upload /absolute/approved-graphic.png --approve-upload
uv run python scripts/factory.py analyze /absolute/reference-sample.mp4 --prompt /absolute/analysis-instructions.md --out /absolute/new-analysis.json --approve-paid-analysis
uv run python scripts/factory.py prepare /absolute/job-packet.json
uv run python scripts/factory.py submit PLAN_ID --approve PLAN_ID
uv run python scripts/factory.py task TASK_ID
```

No user keys belong in any command/packet. Approval flags mean the agent has obtained the corresponding user permission in chat; they are not a way to authorize itself. Prepare is offline and doesn't create paid jobs. It requires a current cost estimate no greater than the user's ceiling, persists the resolved request in private local SQLite, expires after30min and refuses duplicate/ambiguous submissions. Unknown-price jobs stop for a quote. This checks the recorded estimate, not an enforceable provider billing limit. Store generated assets and URL manifests privately; remote URLs should be immutable per-job uploads.

Packet format:

```json
{
  "job": {
    "model": "bytedance/seedance-2-5",
    "input": {
      "prompt": "REPLACE_WITH_APPROVED_SCENES. No subtitles, no captions, no transcript text, no added lower thirds or dialogue overlays.",
      "duration": 5,
      "resolution": "720p",
      "aspect_ratio": "9:16",
      "generate_audio": true,
      "nsfw_checker": true,
      "reference_image_urls": [],
      "reference_audio_urls": []
    }
  },
  "media": [],
  "storyboard_approved": true,
  "approved_budget_usd": 2,
  "estimated_cost_usd": 1.575,
  "cost_note": "Replace with actual current price evidence and user-approved ceiling"
}
```

For every reference URL add `media` entry: `url`, absolute local `path`, `role` (product/graphic/voice/motion_excerpt/continuation), `rights_confirmed:true`. The helper probes local media and fingerprints it. It cannot prove remote URL bytes equal local file; use upload results for that exact file, never change a remote object after preparation. Actual actor description/prompt quality is reviewed by the agent, not inferred by a JSON validator.

Upload helper uses the documented `api.kie.ai/api/file-base64-upload`; it needs a real upload smoke test. No automatic alternate-host retry with a credential. Helper handles<=20MiB; larger files need compression or a separately verified streaming uploader.

## Local integration

This ZIP uses a focused direct-API helper for the exact selected models. Any future connector must preserve those model choices, the secret-store boundary and approval checks.

This local shell-capable Codex flow needs no Kie MCP installation. In a host without shell/filesystem access, a deployed authenticated MCP/tool runtime would be required. Documentation plus a key alone does not grant that runtime.
