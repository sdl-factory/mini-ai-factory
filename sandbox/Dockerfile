# Generation plane: a disposable sandbox where the coding agent works on one task.
# It contains the agent's tools and nothing of yours: no personal credentials, no SSH keys,
# no access to the gateway database. The agent gets two scoped credentials at run time:
# a GitHub token for the agent account, and the project's gateway key.
FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git gh python3 python3-venv python3-pip \
 && rm -rf /var/lib/apt/lists/*

# Pinned agent version, chosen at least two weeks after release. Auto-update is disabled so
# the agent's behaviour only changes when you change this line (and review the change).
RUN npm install -g @anthropic-ai/claude-code@2.1.287
ENV DISABLE_AUTOUPDATER=1

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

USER node
WORKDIR /home/node
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
