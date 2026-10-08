# OpenDesign (od) + opencode CLI jako engine designu.
# Baza: publiczny obraz ghcr.io/nexu-io/od:latest (Alpine 3.24, user open-design/1001).
# Dodajemy tylko: libc6-compat (dla glibc-owego binarium opencode), opencode CLI, shim `od`,
# templatki configu i entrypoint, ktory wstrzykuje config z env przy starcie.
FROM ghcr.io/nexu-io/od:latest

USER root

RUN apk add --no-cache libc6-compat ca-certificates curl bash git git-lfs \
    && npm i -g opencode-ai@1.18.34 \
    && npm cache clean --force

# `od` w obrazie to busybox od — robimy shim na CLI daemona OpenDesign.
RUN printf '#!/bin/sh\nexec node /app/apps/daemon/dist/cli.js "$@"\n' > /usr/local/bin/od \
    && chmod +x /usr/local/bin/od

COPY opencode/opencode.template.json /opt/opencode/opencode.template.json
COPY opencode/init-config.mjs /opt/opencode/init-config.mjs
COPY opencode/init-auth.mjs /opt/opencode/init-auth.mjs
COPY open-design/entrypoint.sh /usr/local/bin/da-entrypoint.sh
RUN chmod +x /usr/local/bin/da-entrypoint.sh \
    && mkdir -p /home/open-design/.config/opencode /home/open-design/.local/share/opencode /home/open-design/.cache \
    && chown -R 1001:1001 /home/open-design

USER open-design
ENV HOME=/home/open-design
EXPOSE 7456
CMD ["/usr/local/bin/da-entrypoint.sh"]
