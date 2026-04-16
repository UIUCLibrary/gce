FROM ghcr.io/astral-sh/uv:latest AS uv_builder

FROM ubuntu:24.04

ARG UBUNTU_APT_PROXY
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=bind,source=./ci/docker/linux/jenkins/apt-packages.txt,target=/tmp/apt-packages.txt\
    <<EOF
      if [ -n "$UBUNTU_APT_PROXY" ]; then
cat <<EOT > /etc/apt/sources.list.d/apt-proxy.sources
Types: deb
URIs: $UBUNTU_APT_PROXY
Suites: noble noble-updates noble-backports noble-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOT
      else \
        echo "APT proxy is not set, using default sources "; \
      fi && \
      apt-get update && \
        < /tmp/apt-packages.txt xargs apt-get install -yqq --no-install-recommends && \
      if [ -n "$UBUNTU_APT_PROXY" ]; then
        rm -f /etc/apt/sources.list.d/apt-proxy.sources && \
        echo "APT proxy sources removed"; \
      fi
EOF
COPY --from=uv_builder /uv /uvx /bin/
