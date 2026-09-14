# Chat-led connections

## Kie

From package root: `uv run python scripts/factory.py setup`.

The helper prints a loopback URL. Open it in the host browser if available. Password entry submits to the local backend, which validates via Kie's credit endpoint and stores in the device's secure credential store. It never returns the secret to the model. The page clears the field and displays connection status. Use `uv run python scripts/factory.py status --setup-url URL` to check that server's sanitized status once; repeat with a short bounded delay while user is actively entering the key. No recurring automation or indefinite polling. The server expires after 15 minutes.

If a key is already stored, `uv run python scripts/factory.py check` performs a read-only credential check. The allowlisted backends are macOS Keychain, Windows Credential Manager and Linux Secret Service. Linux needs an unlocked collection and desktop D-Bus session. Missing or locked storage fails safely; no plaintext or arbitrary third-party backend fallback. Windows/Linux routing is unit-tested but native integration testing is still required. This is a local desktop package, not a hosted browser/mobile application.

Never pass the key on a command line, read it into chat, screenshot the password UI after typing, save browser state containing it, or write it to a file. Secure credential storage may require system authorization. Connection checks do not create generation jobs. Keep customer-facing copy free of recording instructions and creator-specific assumptions.

## Whop, inside chat

Discover live tools first. If unavailable: “Next, install and connect Whop from Plugins. Once you’ve finished, tell me and I’ll check the connection.” Use a host-native installation action only when it is actually available and eligible for that exact plugin. Do not invent one or install a lookalike.

After the user says done, re-discover tools, then minimally verify account/business access. If tools are session-scoped, save a resume summary and ask to continue in a new chat. Installing an onboarding-only skill does not connect the live API.

Official Whop live API MCP: `https://mcp.whop.com/mcp`; browser OAuth happens on Whop. Documentation MCP `https://docs.whop.com/mcp` is not a business connection. Use a custom MCP flow only if supported and the user chooses it. Do not write tokens into configuration. If no live connection exists, continue local creative work and label Whop draft automation unavailable.

## Ready states

Report separately: Kie credential verified; analysis media route tested/unverified; generation routes tested/unverified; Whop authenticated/tool capabilities; FFmpeg available. Never infer Ads readiness from no active campaigns. No account creation/payment authorizations are implied by setup.
