# wob — 12h autonomy agenda (armed 2026-08-22 ~09:20)

## DONE this session (verified)
- Overnight 70-keyword harvest scan finished: deals 287 -> 1,977 (+1,690)
- CLI redesign (uv/Claude-Code aesthetic): theme.py + all commands re-rendered, compiled, forced-color verified
- npm bootstrap package BUILT + install-tested clean (venv auto-provisions, deps OK, data relocates to ~/.local/share/wob on foreign machines)
- requirements.txt corruption fixed (requests/ipython were glued together)

## BLOCKED — needs Connor (1 minute each)
1. **npm publish**: token needs re-auth (npm now wants granular/2FA flow).
   Run in any terminal: `npm login`  (then agent runs `npm publish` again — tarball + package ready)
2. **eBay keys**: register app at developer.ebay.com, put EBAY_APP_ID + EBAY_ACCESS_TOKEN in ~/.config/wob/.env

## Resume queue (next agent session, in order)
1. `npm publish` after Connor's npm login (package.json/README all ready; verify `npm view wob-cli`)
2. Amazon live end-to-end (1 paid call, ~$0.002) — parser already docs-shape-fixed
3. `wob history` will start showing drops once re-scans accumulate; run a small `wob scan --term "deep learning" --sites wob --pages 1 --max-hits 200` to seed 2nd snapshots
4. README.md "Install" section: add npm line (`npm i -g wob-cli`) + PyPI later
5. AGENTS.md: note theme.py + npm packaging + data-dir relocation rules
6. Daily cadence (M4): wob alerts --notify + wob coursepack --scan for a pack of the day

## Standing constraints
- Scan lock: one `wob scan` at a time; stale locks self-clear (pid liveness)
- DataForSEO paid providers (googleshopping/amazon) are NOT in default --sites; each uncached call costs ~$0.002; 24h cache in data/provider_cache.json
- Flash fan-outs: retry empties 3-4x, hand-write survivors
- Main session model: v4-pro. Fan-outs: flash-0731 (see ~/.claude/CLAUDE.md "Model routing")