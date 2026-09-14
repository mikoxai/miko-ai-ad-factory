## [Join 1000+ Marketers Inside Content System AI →](https://whop.com/theaicontentsystem/products/ai-content-accelerator-ed/)

# Miko AI Ad Factory

Turn a product and reference video into an original ad, from research and storyboarding to generation, editing and Whop campaign preparation.

## Get started

Download **Code → Download ZIP** and extract it, or clone the repository:

```sh
git clone https://github.com/mikoxai/miko-ai-ad-factory.git
cd miko-ai-ad-factory
```

Open the folder in Codex and send:

> Read skills/miko-ai-ad-factory/SKILL.md and start AI Ad Factory. Begin with Kie setup, then help me connect Whop.

Enter your Kie API key in the local setup form, then connect Whop through Plugins in chat.

## Workflow

1. **Research your product:** brand pages, competitors, Meta Ad Library, Google Ads Transparency and Reddit.
2. **Break down your reference:** dialogue, shots, camera movement, B-roll, graphics and pacing.
3. **Review the storyboard:** adapted script, scene plan, assets and generation costs.
4. **Create the ad:** Gemini analysis, Nano Banana Pro graphics and Seedance 2.5 video through Kie.
5. **Review and refine:** check the result against your approved plan.
6. **Prepare your Whop campaign:** creative, copy, destination, targeting and budget.

You approve generation costs and campaign launch before they happen.

[See the full workflow](AI_AD_FACTORY.md).

## Requirements

- Codex desktop with local folder and terminal access.
- Python 3.11+ through `uv`, FFmpeg and FFprobe.
- A Kie account and API key; a connected Whop account for campaign preparation.
- OS credential storage: macOS Keychain, Windows Credential Manager or Linux Secret Service. Linux needs an unlocked Secret Service and desktop D-Bus session.

## Check setup

```sh
uv run python scripts/factory.py doctor
```
