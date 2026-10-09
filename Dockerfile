FROM python:3.12-slim

WORKDIR /app

# Install the package (playwright is an optional extra, not needed server-side)
COPY pyproject.toml ./
COPY pta_mcp ./pta_mcp/
RUN pip install --no-cache-dir .

# Default to streamable-http transport bound to all interfaces.
# Cloud hosts inject PORT automatically.
ENV MCP_TRANSPORT=http
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "pta_mcp.server"]
