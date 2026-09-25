# OwnIt backend. Builds KenLM (lmplz/build_binary + Python module), installs the
# spaCy model and NLTK data, and optionally builds the 5-gram LM at image build time.
#
#   docker build -t ownit-backend backend
#   docker build --build-arg BUILD_LM=1 -t ownit-backend backend   # also builds the LM (~30 min)

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NLTK_DATA=/usr/share/nltk_data \
    OWNIT_DATA_DIR=/app/data

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake libboost-program-options-dev libboost-system-dev \
        libboost-thread-dev libboost-test-dev zlib1g-dev libbz2-dev liblzma-dev git curl \
    && rm -rf /var/lib/apt/lists/*

# KenLM command-line tools
RUN git clone --depth 1 https://github.com/kpu/kenlm.git /opt/kenlm \
    && cmake -S /opt/kenlm -B /opt/kenlm/build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /opt/kenlm/build -j"$(nproc)" --target lmplz build_binary \
    && cp /opt/kenlm/build/bin/lmplz /opt/kenlm/build/bin/build_binary /usr/local/bin/ \
    && rm -rf /opt/kenlm

WORKDIR /app
COPY requirements.txt requirements-build.txt ./
RUN pip install -r requirements-build.txt

COPY scripts ./scripts
RUN python scripts/download_resources.py

COPY app ./app

ARG BUILD_LM=0
RUN if [ "$BUILD_LM" = "1" ]; then python scripts/build_lm.py --max-tokens 60000000; fi

EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "--timeout", "120"]
