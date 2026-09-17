FROM python:3.11.16-alpine3.24

# Runtime dependency used by the action
RUN apk add --no-cache git

COPY ./requirements.txt /app/requirements.txt

# All native dependencies used by this action have Python 3.11
# musllinux wheels, so a compiler toolchain is no longer needed.
RUN python -m pip install \
    --no-cache-dir \
    --only-binary=:all: \
    -r /app/requirements.txt

COPY ./markdown_embed_code /app/markdown_embed_code

ENV PYTHONPATH=/app

WORKDIR /app

CMD ["python", "-m", "markdown_embed_code"]