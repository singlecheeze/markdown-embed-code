FROM python:3.7-alpine

# Runtime dependencies
RUN apk add --no-cache \
    git \
    libffi

COPY ./requirements.txt /app/requirements.txt

# cffi has no usable prebuilt wheel for this Python/Alpine combination,
# so install the compiler and headers needed to build it.
# Remove build dependencies afterward to keep the action image small.
RUN apk add --no-cache --virtual .build-deps \
        build-base \
        libffi-dev \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && apk del .build-deps

COPY ./markdown_embed_code /app/markdown_embed_code

ENV PYTHONPATH=/app

WORKDIR /app

CMD ["python", "-m", "markdown_embed_code"]