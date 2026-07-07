FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir click rich

COPY portablecode/ portablecode/
COPY test-linux.sh .
COPY setup-engram-mock.sh .
COPY verify-transform.py .
RUN chmod +x test-linux.sh setup-engram-mock.sh

RUN mkdir -p /root/.config/opencode/skills/test-skill \
    && mkdir -p /root/.config/opencode/plugins \
    && mkdir -p /root/.config/opencode/commands \
    && mkdir -p /root/.local/share/opencode \
    && mkdir -p /root/.engram

RUN echo '{"name":"test"}' > /root/.config/opencode/opencode.json \
    && echo '# AGENTS' > /root/.config/opencode/AGENTS.md

RUN bash setup-engram-mock.sh

CMD ["bash", "test-linux.sh"]
