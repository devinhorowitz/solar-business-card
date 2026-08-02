#!/bin/bash
#
# Stop hook: refuse to end a turn with work that is not committed and pushed.
#
# WHY THIS LIVES IN THE REPO. This is the CCR launcher's own stop hook, patched.
# The launcher provisions ~/.claude/stop-hook-git-check.sh and registers it in
# ~/.claude/launcher-settings.json, and it REWRITES BOTH on every container start
# -- so a fix applied in place survives until the next provision and no longer.
# That happened twice on 2026-08-02 before the cause was found. The repo copy is
# the durable one; .claude/hooks/install.sh (SessionStart) lays it back down over
# the launcher's path each session, so the launcher's own Stop registration ends
# up executing this file.
#
# THE PATCH is the skip_committers list below. Everything else is the launcher's.
# Keep it that way: re-patch from a fresh provision rather than editing around it,
# so an upstream improvement is not silently reverted by this copy.

# Read the JSON input from stdin
input=$(cat)

# Check if stop hook is already active (recursion prevention)
stop_hook_active=$(echo "$input" | jq -r '.stop_hook_active')
if [[ "$stop_hook_active" = "true" ]]; then
  exit 0
fi

# Check if we're in a git repository - bail if not
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  exit 0
fi

# Bail if there's no remote to push to. Every error path below asks the user
# to "push to the remote branch" — meaningless without a remote, and
# unsatisfiable if signing also requires a source. This case arises when CCR
# was launched against a local repo with no github remote (sources=[]) and
# the container's cwd has a leftover .git from a cached resume.
if [[ -z "$(git remote)" ]]; then
  exit 0
fi

# Check for uncommitted changes (both staged and unstaged)
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "There are uncommitted changes in the repository. Please commit and push these changes to the remote branch." >&2
  exit 2
fi

# Check for untracked files that might be important
untracked_files=$(git ls-files --others --exclude-standard)
if [[ -n "$untracked_files" ]]; then
  echo "There are untracked files in the repository. Please commit and push these changes to the remote branch." >&2
  exit 2
fi

current_branch=$(git branch --show-current)
if [[ -n "$current_branch" ]]; then
  if git rev-parse "origin/$current_branch" >/dev/null 2>&1; then
    upstream="origin/$current_branch"
  else
    upstream="origin/HEAD"
  fi

  # Check for local commits that GitHub will show as "Unverified": either no
  # signature at all (%G? == N), or signed with a committer email other than
  # noreply@anthropic.com (the identity CCR's signing key is registered to).
  # Only run when commit signing is configured. Note: %G? is N for unsigned
  # commits; signed-but-locally-unverifiable commits report B/U/E, so this is
  # a reliable presence check even though CCR doesn't configure local verification.
  #
  # --- THE PATCH ---------------------------------------------------------------
  # Commits GitHub itself authored are EXEMPT. A merge commit created by the
  # "Merge pull request" button is committed by noreply@github.com and signed with
  # GitHub's web-flow key (%G? == E: signed, not locally verifiable); CI's
  # commit-back is committed by its own bot identity. Both show as Verified on
  # GitHub, and neither can be amended from here -- they are already published, so
  # the advice this hook prints is unfollowable and the turn cannot be unblocked.
  #
  # Without the skip, the normal post-merge flow trips it every time: resetting the
  # working branch onto main (what this project does after each PR merge) puts
  # main's own merge commit in "$upstream..HEAD", and the hook flags it.
  skip_committers='^(noreply@github[.]com|kibot-ci@users[.]noreply[.]github[.]com)$'
  if [[ "$(git config --type=bool commit.gpgsign 2>/dev/null)" == "true" ]]; then
    unverifiable=$(git log --format='%h %G? %ce' "$upstream..HEAD" 2>/dev/null \
      | awk -v skip="$skip_committers" '$3 ~ skip { next } $2 == "N" || $3 != "noreply@anthropic.com"')
    if [[ -n "$unverifiable" ]]; then
      echo "There are commit(s) on branch '$current_branch' that GitHub will show as Unverified (missing signature, or committer email is not noreply@anthropic.com):" >&2
      echo "$unverifiable" >&2
      echo "Please run 'git config user.email noreply@anthropic.com && git config user.name Claude', then 'git commit --amend --no-edit --reset-author' for the tip commit, or 'git rebase --exec \"git commit --amend --no-edit --reset-author\" $upstream' for earlier commits, then push." >&2
      exit 2
    fi
  fi

  unpushed=$(git rev-list "$upstream..HEAD" --count 2>/dev/null) || unpushed=0
  if [[ "$unpushed" -gt 0 ]]; then
    if [[ "$upstream" == "origin/$current_branch" ]]; then
      echo "There are $unpushed unpushed commit(s) on branch '$current_branch'. Please push these changes to the remote repository." >&2
    else
      echo "Branch '$current_branch' has $unpushed unpushed commit(s) and no remote branch. Please push these changes to the remote repository." >&2
    fi
    exit 2
  fi
fi

exit 0
