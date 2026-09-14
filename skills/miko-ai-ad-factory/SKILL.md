---
name: miko-ai-ad-factory
description: Run a chat-led, reference-first AI ad workflow with Kie Gemini analysis, Seedance 2.5 video, Nano Banana Pro graphics and separately connected Whop tools. Use when asked to start the AI Ad Factory or adapt a reference into an original product ad and prepare its campaign.
---

# AI Ad Factory

Begin: “Starting AI Ad Factory. First, let’s connect Kie.” Keep the entire orchestration in the user's existing Codex chat. Use the local browser only for secure key entry, provider sign-in and actual app previews. This local kit requires filesystem/shell access; ordinary cloud-only Chat without that runtime cannot execute it by attachment alone.

Package root is two levels above this skill folder. Run helpers from that root with `uv run python scripts/factory.py ...`. Do not install globally. Keep runtime files, credentials and customer media out of shared copies.

## 1. Connect, in order

Read [connections.md](references/connections.md). Start the local `setup` helper; show its URL in the host's browser panel. Never inspect the password field, capture its contents or ask for the key in chat. Check sanitized setup status; after verified credentials say “Kie connected. Next, let’s connect Whop.” Saved credentials are not proof that every model/media route works.

Discover available Whop tools in the current host. If missing, guide native plugin installation/account connection in chat; wait for the user to finish, then re-discover and perform a minimal read-only identity/capability check. “Installed” is not “authenticated.” A guidance-only Whop skill is not a live connection. Preserve a resume summary if a new chat is required. Do not fabricate a connection prompt/tool/deep link or promise the host can install every plugin from chat. Whop CLI is not a required onboarding step for this version.

## 2. Intake and evidence

Collect product/offer/approved claims and product images; uploaded reference video; target duration/aspect ratio; optional licensed/consented voice sample for each speaker. Ask only for missing choices. Explain that supplied media selected for provider analysis/generation is uploaded to Kie and that paid work needs approval. Complete [research.md](references/research.md): brand/product truth, Google/competitor research, Meta Ad Library, Google Ads Transparency and required Reddit customer research. Collect actual evidence using available browser/search/MCP tools. Save the sourced brief and creative handoff; any incomplete source track requires explicit limited-research acceptance before advancing. A query plan alone is not completed research.

Read [reference-analysis.md](references/reference-analysis.md). Analyze the full uploaded reference. Reuse an analysis method, never a fixed example-derived editing preset. If host delegation is available, use bounded parallel visual-evidence and Gemini-analysis workers, then reconcile. Never delegate secret entry or claim FFmpeg semantically analyzes frames.

## 3. Adapt and approve

Read [production.md](references/production.md). Write the full scene outline using [storyboard.md](references/storyboard.md). Every cut, zoom, B-roll purpose and graphic animation comes from the current reference unless the user approves a departure. Replace wording, product actions and unsupported claims appropriately. Show scene timing, dialogue, visual treatment, reference asset map, voice assignment and cost before asking for approval. Include graphical asset generation in that approval budget.

## 4. Assets and generation

Characters are described in text directly to Seedance 2.5. Do not generate character stills or silently impose an image-conditioned casting workflow. Product photos and prepared graphics are permitted image references. Voice samples are optional and separately bound to speakers in the prompt. Reference audio influences delivery; do not guarantee exact cloning or perfect two-speaker assignment.

Prepare complex editorial graphics using Nano Banana Pro through Kie; review and correct their text before using them as Seedance image references. A reference screenshot may inform graphic layout, but remove its subtitles and replace its product, branding and unverified assertions. Do not fabricate publications, experts or studies. Explicitly describe how the resulting graphic should move, when it appears and when to cut away.

Use exact models and validated request contracts in [provider-contracts.md](references/provider-contracts.md). Do not substitute Nano Banana 2 for Pro. Do not upload the complete source ad to Seedance by default. A specifically selected, authorized animation/video excerpt may be used when the approved plan calls for it; this is distinct from analysis of the full source. Generated continuation clips are a separate reference role.

Every Seedance prompt includes: **“No subtitles, no captions, no transcript text, no added lower thirds or dialogue overlays.”** This excludes captions, not approved text within an editorial graphic/product label. No automatic caption-burning later either; user must request it.

Prepare each paid job with the helper; show the resolved input and quote status. Submit only after explicit chat approval for that plan and cost; use the approval ID. Keep retries bounded; ambiguous submissions stop for reconciliation instead of resubmitting. Preserve returned task IDs and check status in bounded intervals, with user progress updates. Do not promise frame-exact model timing.

## 5. QA, campaign and stop

Review all generated footage against the approved reference-derived plan. Fix missed timing/crops/text deterministically or regenerate the affected asset with approval. Do not apply an unrelated zoom formula. Preserve originals. Metadata cleanup is an optional privacy/export step, never a promise of ban avoidance; preserve required provenance/disclosures.

Read [whop-demo.md](references/whop-demo.md). Prepare a local campaign preview first. Use native Whop tools only where discovered/supported and authorized. Default to a non-delivering draft; funding, launch and spend changes require separate explicit approval. A daily reporting routine is a proposal until explicitly scheduled; creatives and budget changes require defined authority.

Deliver the reviewed ad, scene plan, prompts/assets manifest, costs, QA notes and campaign preview. Mark skipped/unverified steps. Save reusable templates without client secrets/private media. Do not claim production readiness while authenticated integration tests remain outstanding. Treat the user as a customer running their own workflow, not a creator filming a sponsor demonstration.
