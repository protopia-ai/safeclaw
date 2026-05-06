# OpenClaw with Google Cloud SDK and gogcli installed.
FROM ghcr.io/openclaw/openclaw:latest
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
	ca-certificates \
	curl \
	gnupg \
	apt-transport-https \
	build-essential
RUN mkdir -p /etc/apt/keyrings \
	&& curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
	| gpg --dearmor -o /etc/apt/keyrings/cloud.google.gpg \
	&& echo "deb [signed-by=/etc/apt/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
	> /etc/apt/sources.list.d/google-cloud-sdk.list

# Install the Google Cloud SDK
RUN apt-get update && apt-get install -y --no-install-recommends \
	google-cloud-sdk \
	&& rm -rf /var/lib/apt/lists/*

RUN mkdir -p /home/linuxbrew/.linuxbrew \
	&& chown -R node:node /home/linuxbrew

COPY --chown=node:node examples/ /opt/safeclaw-examples/

USER node

# Install brew
ENV NONINTERACTIVE=1
RUN curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash
ENV PATH="/home/linuxbrew/.linuxbrew/bin:/home/linuxbrew/.linuxbrew/sbin:${PATH}"

# Install gogcli
RUN brew install steipete/tap/gogcli

COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

