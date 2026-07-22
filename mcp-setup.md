# MCP setup handoff -- distributor part APIs (DigiKey + Mouser)

**Purpose.** Stand up the DigiKey and Mouser MCP servers so a session can pull live part
pricing / stock / specs into the BOM work -- e.g. the SS17 `3-153-440` unit price still marked
**TBC** in `PCB/solar-glow-drh-v4_0-BOM.xlsx`. This doc exists so a fresh session can finish the
job cold, without cross-chat.

## Status

**2026-07-22 (latest) -- BOTH DISTRIBUTOR APIs NOW LIVE; the BOM is fully priced.** DigiKey and
Mouser both return live data; every ordered on-board line has a price. (Earlier in the day the Mouser
key was still rejected -- see the Mouser bullet -- but it has since come live.) Went straight to live
API calls (no MCP wrapper needed to prove connectivity):
- **Network policy now permits both hosts.** `https://api.digikey.com` -> `404` and
  `https://api.mouser.com` -> `302` (real HTTP responses, not the old `000` / `CONNECT tunnel failed`).
  General web is partly open too (`example.com` -> `200`; `www.digikey.com` still `403`). The two API
  hosts we need are reachable.
- **Credentials are now set.** `DIGIKEY_CLIENT_ID` (48 ch), `DIGIKEY_CLIENT_SECRET` (64 ch),
  `MOUSER_PART_API_KEY` (36-ch GUID) are all present in the container.
- **DigiKey: WORKING.** OAuth2 client_credentials returned a bearer token (HTTP 200), and a
  Product Information V4 `keyword` search returned live data. Results used to close the BOM TBC:
  - **SS17 `3-153-440`** (DK `486-3-153-440-ND`): **$17.16 @ 1**, 200 in stock (10@$13.48, 100@$11.55).
  - **WS17 `3-153-438`** (DK `486-3-153-438-ND`): **$16.69 @ 1**, 195 in stock (was $15.48 @ 2026-07-02).
  Both written into `PCB/solar-glow-drh-v4_0-BOM.xlsx` (SC1/SC3 row filled; SC2/SC4 refreshed;
  subtotal recomputed to $130.00 / 30 priced cells).
- **Mouser: WORKING (now).** Earlier in the day `search/partnumber` returned HTTP 200 with
  `{Code: "Invalid", Message: "Invalid unique identifier", PropertyName: "API Key"}` -- the key was not
  yet an activated Search key. It has since come live: `search/partnumber` for `10AEM10300C0000` returns
  the real listing and closed the last BOM line:
  - **U8 (AEM10300)** -> Mouser `120-AEM10300-QFN` (e-peas), **$3.77 @ 1**, 553 in stock, 16-day lead
    (breaks 10@$2.81, 100@$2.31, 1000@$1.85). Written into `PCB/solar-glow-drh-v4_0-BOM.xlsx` (`R35`).
  U8 is the only Mouser-only line (DigiKey returns 0 results for it); everything else is DigiKey-sourced.
- **MCP registration is optional now.** DigiKey's data was pulled directly (curl/`requests` through the
  proxy CA), so the BOM job is done without the MCP servers. To make `digikey` / `mouser` tools available
  to future *interactive* sessions, put `scripts/setup-distributor-mcp.sh` in the **environment setup
  script** (a mid-session `claude mcp add` only affects the current ephemeral container and does not
  hot-load into an already-running session). The script stays valid; only the Mouser key needs fixing.

_Prior status (2026-07-22, earlier sessions): servers cloned + `uv sync`'d + smoke-tested, then blocked
first by the egress `403`, then by unset credentials, then by an unactivated Mouser Search key. All
three are now resolved -- both APIs are live and the BOM is fully priced._

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

- **DigiKey -- DONE 2026-07-22.** `keyword` search for `3-153-440` (SS17) and `3-153-438` (WS17) both
  returned live pricing/stock; the SS17 TBC is filled and the WS17 refreshed in
  `PCB/solar-glow-drh-v4_0-BOM.xlsx` (see Status).
- **Mouser -- DONE 2026-07-22.** `search_by_part_number` for `10AEM10300C0000` returned the live listing
  (`120-AEM10300-QFN`, $3.77 @ 1, 553 in stock); the U8 (`R35`) price/stock is filled in the BOM (see Status).

## Security

- Keys live only in environment variables + each clone's `.env` (gitignored, outside this repo).
  Never commit them.
- The DigiKey Client ID/Secret were pasted into a chat transcript during setup. Rotate them once on
  the app page if that matters (regenerating is one click), then update the env var.
