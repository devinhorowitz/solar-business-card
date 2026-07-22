#!/usr/bin/env sh
# setup-distributor-mcp.sh -- stand up the DigiKey + Mouser part-API MCP servers.
#
# One-command version of the steps in ../mcp-setup.md. Safe to re-run (idempotent):
# it clones each server if missing (else fast-forwards), uv-syncs, writes each
# clone's gitignored .env from environment variables, and registers both with
# `claude mcp add`. Run it from an environment setup script, or by hand in a fresh
# session after the two prerequisites below are satisfied.
#
# PREREQUISITES (both are environment settings; both take effect only in a NEW
# container/session -- see ../mcp-setup.md):
#   1. Network policy allows outbound HTTPS to api.digikey.com AND api.mouser.com.
#   2. These env vars are set:  DIGIKEY_CLIENT_ID  DIGIKEY_CLIENT_SECRET  MOUSER_PART_API_KEY
#
# Nothing here is written into the board repo: clones live under $CLONE_ROOT
# (default /home/user) and each clone's .env is gitignored by that clone.
set -eu

CLONE_ROOT="${CLONE_ROOT:-/home/user}"
DIGIKEY_DIR="$CLONE_ROOT/digikey_mcp"
MOUSER_DIR="$CLONE_ROOT/mouser-mcp-docker"
DIGIKEY_REPO="https://github.com/bengineer19/digikey_mcp.git"
MOUSER_REPO="https://github.com/nickweedon/mouser-mcp-docker.git"

say() { printf '\n=== %s ===\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

# --- preflight ------------------------------------------------------------
say "preflight"
for bin in git uv claude; do
  have "$bin" || { echo "FATAL: '$bin' not on PATH"; exit 1; }
done

missing=""
for v in DIGIKEY_CLIENT_ID DIGIKEY_CLIENT_SECRET MOUSER_PART_API_KEY; do
  eval "val=\${$v:-}"
  [ -n "$val" ] || missing="$missing $v"
done
if [ -n "$missing" ]; then
  echo "FATAL: missing required env var(s):$missing"
  echo "       Set them in the environment settings (a NEW session picks them up), then re-run."
  exit 1
fi

# Best-effort reachability check -- a 403 here means the network policy still
# blocks the host, so the servers will load but every query will fail.
say "network reachability (best effort)"
for host in api.digikey.com api.mouser.com; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "https://$host" 2>/dev/null || echo 000)"
  if [ "$code" = "000" ]; then
    echo "WARN: https://$host not reachable (egress 403 / CONNECT refused?) -- queries will fail until the network policy allows it."
  else
    echo "ok:   https://$host reachable (HTTP $code)"
  fi
done

# --- clone + sync helper --------------------------------------------------
clone_sync() {
  dir="$1"; repo="$2"
  if [ -d "$dir/.git" ]; then
    echo "update: $dir"
    git -C "$dir" fetch --depth 1 origin >/dev/null 2>&1 || true
    git -C "$dir" reset --hard origin/HEAD >/dev/null 2>&1 || \
      git -C "$dir" pull --ff-only >/dev/null 2>&1 || true
  else
    echo "clone:  $repo -> $dir"
    git clone --depth 1 "$repo" "$dir"
  fi
  uv sync --directory "$dir"
}

# --- DigiKey (bengineer19/digikey_mcp) ------------------------------------
say "DigiKey MCP"
clone_sync "$DIGIKEY_DIR" "$DIGIKEY_REPO"
# Server reads CLIENT_ID / CLIENT_SECRET (NOT the DIGIKEY_-prefixed names) via load_dotenv().
# USE_SANDBOX is deliberately left UNSET: the code treats USE_SANDBOX=false as "use sandbox"
# (os.getenv("USE_SANDBOX","true").lower()=="false"), the inverse of its README. Unset == production.
umask 077
printf 'CLIENT_ID=%s\nCLIENT_SECRET=%s\n' "$DIGIKEY_CLIENT_ID" "$DIGIKEY_CLIENT_SECRET" > "$DIGIKEY_DIR/.env"
echo "wrote:  $DIGIKEY_DIR/.env (CLIENT_ID/CLIENT_SECRET, production endpoint)"

# --- Mouser (nickweedon/mouser-mcp-docker) --------------------------------
say "Mouser MCP"
clone_sync "$MOUSER_DIR" "$MOUSER_REPO"
# Run the plain Python script (uv run mouser-mcp); ignore the repo's shipped .mcp.json
# (it is a mispasted Playwright config). Only the Part Search key is needed.
printf 'MOUSER_PART_API_KEY=%s\n' "$MOUSER_PART_API_KEY" > "$MOUSER_DIR/.env"
echo "wrote:  $MOUSER_DIR/.env (MOUSER_PART_API_KEY)"

# --- register both --------------------------------------------------------
say "register MCP servers"
# remove-then-add so re-runs don't error on an existing entry
claude mcp remove digikey >/dev/null 2>&1 || true
claude mcp remove mouser  >/dev/null 2>&1 || true
claude mcp add digikey -- uv run --directory "$DIGIKEY_DIR" python digikey_mcp_server.py
claude mcp add mouser  -- uv run --directory "$MOUSER_DIR" mouser-mcp

say "done"
echo "Registered 'digikey' and 'mouser'. Start a fresh session for the tools to load, then e.g.:"
echo "  digikey get_product_pricing / keyword_search  ->  3-153-440 (SS17), 3-153-438 (WS17)"
echo "  mouser  search_by_part_number                 ->  AEM10300 (U8), the SCHURTER supercaps"
