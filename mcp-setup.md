# MCP setup handoff -- distributor part APIs (DigiKey + Mouser)

**Purpose.** Stand up the DigiKey and Mouser MCP servers so a session can pull live part
pricing / stock / specs into the BOM work -- e.g. the SS17 `3-153-440` unit price still marked
**TBC** in `PCB/solar-glow-drh-v4_0-BOM.xlsx`. This doc exists so a fresh session can finish the
job cold, without cross-chat.

## Status

**2026-07-22 (re-verified in a fresh container) -- STILL BLOCKED on environment config.**
A new session re-checked both gates; neither is satisfied yet:
- **Network policy still denies both hosts.** From a fresh container, `curl` to `api.digikey.com`
  and `api.mouser.com` both returned `403 CONNECT tunnel failed` at the egress gateway (proxy
  `recentRelayFailures` = `connect_rejected` for both). The allowlist currently reaches GitHub +
  PyPI only; *all* general internet (even `www.digikey.com`, `example.com`) is 403'd. So the
  "network enabled 2026-07-22" change **has not taken effect** -- the environment's network policy
  must be edited to permit `api.digikey.com` and `api.mouser.com`, and (like all policy/env changes)
  it only applies in a **new** session, not a live one.
- **Credentials are not set.** `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET`, `MOUSER_PART_API_KEY`
  are all unset in the container. Add them in the environment settings (never in chat/repo); they too
  take effect only in a new session.
- **Setup is otherwise ready and source-verified.** Both servers were cloned in this session and
  every command below was checked against the actual server code (entry points, env-var names, and
  the DigiKey `USE_SANDBOX` inversion all confirmed -- see per-server notes). The whole flow is now
  captured as a one-command, idempotent script: **`scripts/setup-distributor-mcp.sh`**. Once the two
  gates above are green in a fresh session, run that script (or the manual steps below) and the
  `digikey` / `mouser` tools load.

_Prior status (2026-07-22, earlier session): both servers cloned, `uv sync`'d, and smoke-tested;
blocked solely by the network policy (egress `403`). That remains the sole substantive blocker,
now joined by the still-unset credentials in the current container._

## Prerequisites

1. **Network policy** must allow outbound HTTPS to `api.digikey.com` and `api.mouser.com`
   (enabled 2026-07-22; effective in a new container).
2. **Runtimes** already present in the CCR environment: `uv`, python 3.11, git. `requests` honors
   `REQUESTS_CA_BUNDLE` (the proxy CA), so TLS through the egress proxy works once the host is allowed.
3. **Credentials as environment variables** (set in the environment settings -- not in chat, not in
   the repo):
   - `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET` -- from developer.digikey.com: a **Production App**
     with the **Product Information V4** product enabled, client-credentials grant (no callback URL).
   - `MOUSER_PART_API_KEY` -- from mouser.com/api-hub -> **Search API** (the Order/Cart key is not
     needed). The Search key requires an access-request form with approval lag, so request it early.

## Per-container setup (put this in the environment setup script)

**Shortcut:** `scripts/setup-distributor-mcp.sh` runs everything below in one idempotent step
(preflight-checks the creds + host reachability, clones/`uv sync`s both, writes each `.env`, and
registers both servers). The manual steps are equivalent and kept here for reference.

Clones live outside any repo (e.g. `/home/user`) so nothing here touches the board repo:

```sh
# DigiKey -- bengineer19/digikey_mcp (Python; DigiKey Product Information V4)
git clone https://github.com/bengineer19/digikey_mcp.git /home/user/digikey_mcp
uv sync --directory /home/user/digikey_mcp
printf 'CLIENT_ID=%s\nCLIENT_SECRET=%s\n' "$DIGIKEY_CLIENT_ID" "$DIGIKEY_CLIENT_SECRET" > /home/user/digikey_mcp/.env

# Mouser -- nickweedon/mouser-mcp-docker (run as plain Python, NOT its shipped .mcp.json)
git clone https://github.com/nickweedon/mouser-mcp-docker.git /home/user/mouser-mcp-docker
uv sync --directory /home/user/mouser-mcp-docker
printf 'MOUSER_PART_API_KEY=%s\n' "$MOUSER_PART_API_KEY" > /home/user/mouser-mcp-docker/.env

# register both (they load at session start)
claude mcp add digikey -- uv run --directory /home/user/digikey_mcp python digikey_mcp_server.py
claude mcp add mouser  -- uv run --directory /home/user/mouser-mcp-docker mouser-mcp
```

Manual alternative (no env config): start a fresh session, provide the keys, and run the same
clone / `uv sync` / `.env` / `claude mcp add` steps by hand.

## Per-server notes and gotchas

### DigiKey -- `bengineer19/digikey_mcp`
- API: Product Information V4 (`/products/v4/search/...`); auth: OAuth2 **client_credentials**
  (no callback URL needed).
- Tools: `keyword_search`, `product_details`, `get_product_pricing`, `search_product_substitutions`,
  `get_product_media`, `search_manufacturers`, `search_categories`, `get_category_by_id`, digireel pricing.
- It **fetches the OAuth token at startup**, so it will not launch without valid creds.
- **Gotcha:** `USE_SANDBOX` is inverted vs the README. **Leave it unset** for production
  (`api.digikey.com`). Setting `USE_SANDBOX=false` selects the sandbox (fake data), despite what the
  README says. Only set it to `false` to deliberately test against sandbox.

### Mouser -- `nickweedon/mouser-mcp-docker`
- A `fastmcp` Python server packaged in Docker. Docker is optional -- run it directly with
  `uv run mouser-mcp` (the `pyproject.toml` exposes that script).
- **Ignore the repo's shipped `.mcp.json`** -- it is a wrong copy-paste (a Playwright config), not Mouser.
- Needs only `MOUSER_PART_API_KEY` (Search API) for part search/pricing. Imports fine without keys;
  keys are read per call.
- Tools: `search_by_keyword`, `search_by_part_number` (plus cart/order tools that need the unused
  Order key).

## First queries once live

- **DigiKey:** `get_product_pricing` / `keyword_search` for `3-153-440` (SS17) -> fill the TBC price in
  `PCB/solar-glow-drh-v4_0-BOM.xlsx`, and cross-check the WS17 `3-153-438`.
- **Mouser:** `search_by_part_number` for the AEM10300 (U8) and the two SCHURTER supercaps.

## Security

- Keys live only in environment variables + each clone's `.env` (gitignored, outside this repo).
  Never commit them.
- The DigiKey Client ID/Secret were pasted into a chat transcript during setup. Rotate them once on
  the app page if that matters (regenerating is one click), then update the env var.
