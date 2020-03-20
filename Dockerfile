FROM python:3.8-slim

ARG ENVIRONMENT="production"

ENV POETRY_VERSION="1.0.5"
ENV APP_ENVIRONMENT=${ENVIRONMENT}
ENV PYTHONUNBUFFERED=1

RUN pip install "poetry==$POETRY_VERSION"

RUN poetry config virtualenvs.create false

WORKDIR /app/

COPY poetry.lock pyproject.toml ./

COPY milestones_to_markdown ./milestones_to_markdown/

RUN if [ "$APP_ENVIRONMENT" = "production" ]; then poetry install --no-dev; else poetry install; fi

ENTRYPOINT [ "milestones-to-markdown"]
CMD []
