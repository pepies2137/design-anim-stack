# motion-anything (+ opencode CLI + caddy z basic auth)
# Upstream: https://github.com/nexu-io/motion-anything — zero zaleznosci npm, Node 18+.
# Debian slim (glibc), bo opencode jest linkowany dynamicznie do glibc (na Alpine potrzebny libc6-compat).
FROM node:22-bookworm-slim

ARG MA_REF=main
ARG OPENCODE_VERSION=1.18.34
ARG CADDY_VERSION=2.10.0

RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates curl bash tini python3 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# caddy: reverse proxy z basic auth przed workbenchem (motion-anything nie ma wlasnego auth)
RUN curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_amd64.tar.gz" \
      -o /tmp/caddy.tgz \
    && tar -xzf /tmp/caddy.tgz -C /usr/local/bin caddy \
    && rm /tmp/caddy.tgz \
    && caddy version

RUN git clone --depth 1 --branch "${MA_REF}" https://github.com/nexu-io/motion-anything.git /app \
    && rm -rf /app/.git

RUN npm i -g "opencode-ai@${OPENCODE_VERSION}" && npm cache clean --force

COPY motion-anything/patch-motion.py /tmp/patch-motion.py
RUN python3 /tmp/patch-motion.py /app/cli/bin/motion.js

COPY opencode/opencode.template.json /opt/opencode/opencode.template.json
COPY opencode/init-config.mjs /opt/opencode/init-config.mjs
COPY opencode/init-auth.mjs /opt/opencode/init-auth.mjs
COPY motion-anything/entrypoint.sh /usr/local/bin/ma-entrypoint.sh

ENV HOME=/home/ma
RUN chmod +x /usr/local/bin/ma-entrypoint.sh \
    && mkdir -p /home/ma/.config/opencode /home/ma/.local/share/opencode /home/ma/.cache \
       /app/app/projects /app/app/user-skills /etc/caddy \
    && chown -R node:node /home/ma /app /etc/caddy

WORKDIR /app
USER node
EXPOSE 4399
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=20s \
  CMD node -e "fetch('http://127.0.0.1:4398/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/local/bin/ma-entrypoint.sh"]
