# Match the interpreter pinned in .python-version so the lockfile's wheels line up.
FROM python:3.10-slim

# uv is the project's package manager; copy a static build from its official image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Compile Python bytecode at install time so start-up does not pay for it.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so code edits do not bust the dependency layer.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the project itself. Tests are not copied: they are not needed to run
# the game, and leaving them out keeps the image small.
COPY README.md ./
COPY herd_mentality ./herd_mentality
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    HOST=0.0.0.0 \
    PORT=8000 \
    RELOAD=0

EXPOSE 8000

# The app stores game state in memory, so one worker is the correct setup.
CMD ["uv", "run", "--frozen", "herd-mentality"]
