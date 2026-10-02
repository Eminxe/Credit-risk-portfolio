FROM python:3.12-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg OMP_NUM_THREADS=2
WORKDIR /workspace
COPY pyproject.toml requirements-linux.lock ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements-linux.lock && pip install --no-cache-dir --no-deps -e '.[dev]'
COPY . .
CMD ["python", "scripts/run_pipeline.py"]
