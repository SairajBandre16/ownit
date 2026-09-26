# OwnIt backend + LanguageTool in one image, for Hugging Face Spaces (Docker SDK).
#
# Build context: the repository root (this file copies backend/).
#   docker build -f deploy/hf-space/Dockerfile -t ownit-space .
#   docker run -p 7860:7860 ownit-space
#
# On Spaces, put this Dockerfile, deploy/hf-space/start.sh and backend/ in the Space repo
# (see deploy/hf-space/README.md). The fallback n-gram LM is built at image build time
# (~10 min, downloads WikiText-103); pass --build-arg BUILD_LM=0 to skip it (fluency checks
# are then neutral).

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NLTK_DATA=/home/user/nltk_data \
    OWNIT_DATA_DIR=/home/user/app/data \
    OWNIT_LANGUAGETOOL_URL=http://127.0.0.1:8010 \
    PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as user 1000
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app

COPY --chown=user backend/requirements.txt backend/requirements-build.txt ./
RUN pip install --user -r requirements.txt pyarrow==18.1.0
ENV PATH=/home/user/.local/bin:$PATH

COPY --chown=user backend/scripts ./scripts
RUN python scripts/download_resources.py --languagetool

COPY --chown=user backend/app ./app

ARG BUILD_LM=1
RUN if [ "$BUILD_LM" = "1" ]; then python scripts/build_lm.py --skip-kenlm; fi

COPY --chown=user deploy/hf-space/start.sh ./start.sh
RUN chmod +x start.sh

EXPOSE 7860
CMD ["./start.sh"]
