#!/usr/bin/env bash
#
# watch-agent.sh — follow what a sandcastle agent is *actually* doing.
#
# Sandcastle's stdout view only surfaces the agent's prose plus four allowlisted
# tools (Bash/WebSearch/WebFetch/Agent); Read/Edit/Write/Grep/thinking are
# dropped before display. The full record lives in the raw Claude Code session
# transcript that the `claude` CLI writes to
#   ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl
# This script tails that transcript and pretty-prints it.
#
# Run it in a second pane while `npm start` drives the loop. Each agent in the
# loop gets its own session; since the worktree is the agent's cwd, sessions
# sort under ~/.claude/projects/-...-sandcastle-worktrees-<branch>/.
#
# Usage:
#   ./watch-agent.sh                 # follow the most-recently-touched session
#   ./watch-agent.sh <substr>        # follow newest session whose path matches <substr>
#                                    #   (e.g. a branch name, to pin one worktree)
#   ./watch-agent.sh -l|--list       # list recent sessions (newest first) and exit
#   ./watch-agent.sh -a <substr>     # replay from the start, then follow
#   ./watch-agent.sh -h|--help       # this help
#
# Notes:
#   - tail -f follows ONE file; if a new agent starts a new session, re-run to
#     attach to it (or use --list to see what's live).
#   - Requires jq. Override the transcript root with CLAUDE_PROJECTS if needed.

set -euo pipefail

PROJECTS="${CLAUDE_PROJECTS:-$HOME/.claude/projects}"
FROM_START=0
MATCH=""

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; /^set -euo/d'; }

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -l|--list) LIST=1; shift ;;
    -a|--all)  FROM_START=1; shift ;;
    --)        shift; break ;;
    -*)        echo "unknown flag: $1" >&2; usage; exit 2 ;;
    *)         MATCH="$1"; shift ;;
  esac
done

command -v jq >/dev/null 2>&1 || { echo "jq is required (apt install jq)" >&2; exit 1; }
[ -d "$PROJECTS" ] || { echo "no transcript dir at $PROJECTS" >&2; exit 1; }

# Newest-first list of session files, optionally filtered by a path substring.
sessions() {
  # shellcheck disable=SC2012  -- ls -t for mtime ordering is fine here
  ls -t "$PROJECTS"/*/*.jsonl 2>/dev/null | { [ -n "$MATCH" ] && grep -i -- "$MATCH" || cat; }
}

if [ "${LIST:-0}" = 1 ]; then
  sessions | while read -r f; do
    printf '%s  %s\n' "$(date -r "$f" '+%H:%M:%S')" "$f"
  done
  exit 0
fi

FILE="$(sessions | head -1 || true)"
[ -n "$FILE" ] || { echo "no session transcript found${MATCH:+ matching '$MATCH'} under $PROJECTS" >&2; exit 1; }
echo "tailing $FILE" >&2

# assistant: text 💬, tool calls 🔧 (with full input), thinking 💭
# user:      tool results ↳ (truncated to 500 chars)
FILTER='
  if .type=="assistant" then
    .message.content[]?
    | if   .type=="tool_use" then "🔧 \(.name) \(.input|tostring)"
      elif .type=="text"     then (select((.text//"")!="") | "💬 \(.text)")
      elif .type=="thinking" then "💭 \(.thinking)"
      else empty end
  elif .type=="user" then
    .message.content[]?
    | select(.type=="tool_result")
    | (.content | if type=="array" then (map(.text? // "")|join("")) else tostring end)
    | "↳ \(.[0:500])"
  else empty end
'

TAILARGS=(-n 0 -f)
[ "$FROM_START" = 1 ] && TAILARGS=(-n +1 -f)

tail "${TAILARGS[@]}" "$FILE" | jq -rc "$FILTER"
