from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.shortener import InvalidURLError, shortener

app = FastAPI()


class ShortenRequest(BaseModel):
    url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/shorten", status_code=201)
def shorten(request: ShortenRequest):
    try:
        return shortener.shorten(request.url)
    except InvalidURLError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
