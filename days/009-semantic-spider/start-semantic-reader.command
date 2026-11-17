#!/bin/zsh
cd "$(dirname "$0")"
if ! curl -fsS http://127.0.0.1:8791/health >/dev/null 2>&1; then
  task_node=$(command -v node)
  if [ -z "$task_node" ] && [ -x /opt/homebrew/bin/node ]; then task_node=/opt/homebrew/bin/node; fi
  if [ -z "$task_node" ]; then echo 'Node.js is required to run the local OpenAI relay.'; read -r; exit 1; fi
  "$task_node" semantic-reader-server.cjs &
fi
open http://127.0.0.1:8791
wait
