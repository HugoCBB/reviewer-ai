import hashlib
import hmac

from fastapi import FastAPI, Header, HTTPException, Request

from api.tasks import review_pr
from app.core.config import settings



app = FastAPI(title="Reviewer AI")


def _verify_signature(payload: bytes, signature: str) -> bool:
    """Validate GitHub webhook HMAC-SHA256 signature."""
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_hub_signature_256: str = Header(...),
):
    payload_bytes = await request.body()

    if not _verify_signature(payload_bytes, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    # Apenas pr abertos ou novos commits
    if x_github_event == "pull_request" and payload.get("action") in (
        "opened",
        "synchronize",
    ):
        pr = payload["pull_request"]
        review_pr.delay({
            "number": pr["number"],
            "repo":   payload["repository"]["full_name"],
            "title":  pr["title"],
            "body":   pr.get("body"),
        })

    return {"status": "accepted"}


@app.get("/health")
def health():
    return {"status": "ok"}