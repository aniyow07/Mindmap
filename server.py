"""Local web app: `uvicorn server:app --reload`, then open http://localhost:8000."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles

from automap.mindmap import build_mindmap

MAX_BYTES = 25 * 1024 * 1024
WEB = Path(__file__).parent / "web"

app = FastAPI(title="AutoMap")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/map")
async def make_map(file: UploadFile) -> dict:
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "That PDF is over 25 MB. Try a smaller file.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(415, "That file isn't a PDF.")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upload.pdf"
        path.write_bytes(data)
        try:
            mindmap = await run_in_threadpool(build_mindmap, path)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
    result = mindmap.to_dict()
    if file.filename:
        result["stats"]["file"] = file.filename
    return result


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
