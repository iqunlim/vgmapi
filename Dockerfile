FROM python:3.10-alpine AS base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1  

RUN apk update && \
        apk add musl-dev libpq-dev gcc && \
        adduser -DS python && \
        addgroup python

WORKDIR /api

RUN mkdir ./logs && chown python:python ./logs

USER python

RUN python3 -m pip install --upgrade pip

COPY --chown=python:python requirements.txt .

RUN --mount=type=cache,target=/api/.cache/pip \
        python3 -m pip install -r requirements.txt

EXPOSE 5000

FROM base AS prod

COPY --chown=python:python ./api ./api

CMD ["python3", "-m", "uvicorn", "api.main:create_app", "--host", "0.0.0.0", "--port", "5000", "--factory"]

