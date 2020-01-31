FROM brewblox/brewblox-service:newest-tag as base

COPY ./dist /app/dist
COPY ./requirements.txt /app/requirements.txt

RUN pip3 install wheel \
    && ls /wheeley-base \
    && pip3 wheel --wheel-dir=/wheeley --find-links=/wheeley-base -r /app/requirements.txt \
    && pip3 wheel --wheel-dir=/wheeley --find-links=/wheeley --no-index /app/dist/*

FROM python:3.8-slim
EXPOSE 5001
WORKDIR /app

ARG service_info=UNKNOWN
ENV SERVICE_INFO=${service_info}
ENV PYTHONPATH="/usr/lib/python3/dist-packages:${PYTHONPATH}"

COPY --from=base /wheeley /wheeley
COPY ./config /app/config

RUN \
    apt-get clean && \
    apt-get update && \
    apt-get install -y \
    libglib2.0-dev \
    libatlas3-base \
    python3-bluez

RUN pip3 install --no-index --find-links=/wheeley brewblox-tilt \
    && rm -rf /wheeley \
    && pip3 freeze

ENTRYPOINT ["python3", "-m", "brewblox_tilt"]
