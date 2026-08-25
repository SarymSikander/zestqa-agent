import os
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import Client, create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
HF_TOKEN = os.getenv("HF_TOKEN")
HF_USERNAME = os.getenv("HF_USERNAME", "sarimsikander")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(title="ZestQA Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Only these hosts may be pinged by /platform/verify-hf-space — without this,
# the endpoint is an open SSRF proxy: a caller could pass an internal URL
# (http://169.254.169.254/..., http://localhost:xxxx) and use this server to
# probe its own network.
ALLOWED_HF_HOST_SUFFIXES = (".hf.space", "huggingface.co")


# ── Auth helpers ─────────────────────────────────────────────────────────────

def _bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth.split(" ", 1)[1].strip()


def require_user(request: Request):
    """Validate the caller's Supabase JWT and return their user id + role."""
    token = _bearer_token(request)
    try:
        result = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = getattr(result, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    profile = (
        supabase.table("profiles").select("role").eq("id", user.id).single().execute()
    )
    role = profile.data["role"] if profile.data else "user"
    return {"id": user.id, "role": role}


def require_self_or_admin(user_id: str, caller: dict = Depends(require_user)):
    if caller["id"] != user_id and caller["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized for this user")
    return caller


def require_admin(caller: dict = Depends(require_user)):
    if caller["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return caller


def _require_self_or_admin_for(user_id: str, caller: dict):
    """Same check as require_self_or_admin, for handlers where user_id comes
    from the request body rather than the URL path (so it can't be a path
    dependency)."""
    if caller["id"] != user_id and caller["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized for this user")


# ── Health ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Theme ─────────────────────────────────────────────────────────────────

class ThemeBody(BaseModel):
    sidebar_start: str | None = None
    sidebar_end: str | None = None
    navbar_start: str | None = None
    navbar_end: str | None = None
    hero_start: str | None = None
    hero_end: str | None = None
    primary_color: str | None = None
    logo_base64: str | None = None
    project_name: str | None = None


@app.get("/platform/users/{user_id}/theme")
def get_theme(user_id: str, caller: dict = Depends(require_self_or_admin)):
    res = supabase.table("themes").select("*").eq("user_id", user_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No theme found for this user")
    return res.data


@app.post("/platform/users/{user_id}/theme")
def save_theme(user_id: str, body: ThemeBody, caller: dict = Depends(require_self_or_admin)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    res = supabase.table("themes").update(updates).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No theme row for this user")
    return res.data[0]


class ThemeUpsertRequest(BaseModel):
    user_id: str
    sidebar_start: str = "#151939"
    sidebar_end: str = "#421b70"
    navbar_start: str = "#151939"
    navbar_end: str = "#421b70"
    hero_start: str = "#7e56ef"
    hero_end: str = "#463cb8"
    primary_color: str = "#7e56ef"
    logo_base64: str | None = None
    project_name: str | None = None


@app.post("/platform/theme")
async def upsert_theme(req: ThemeUpsertRequest, caller: dict = Depends(require_user)):
    _require_self_or_admin_for(req.user_id, caller)
    try:
        supabase.table("themes").upsert({
            "user_id": req.user_id,
            "sidebar_start": req.sidebar_start,
            "sidebar_end": req.sidebar_end,
            "navbar_start": req.navbar_start,
            "navbar_end": req.navbar_end,
            "hero_start": req.hero_start,
            "hero_end": req.hero_end,
            "primary_color": req.primary_color,
            "logo_base64": req.logo_base64,
            "project_name": req.project_name,
        }).execute()
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/platform/theme/{user_id}")
async def get_theme_by_id(user_id: str, caller: dict = Depends(require_self_or_admin)):
    try:
        result = supabase.table("themes").select("*").eq("user_id", user_id).single().execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Profile ───────────────────────────────────────────────────────────────

@app.get("/platform/profile/{user_id}")
async def get_profile(user_id: str, caller: dict = Depends(require_self_or_admin)):
    try:
        result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Integrations ─────────────────────────────────────────────────────────

class IntegrationsBody(BaseModel):
    jira_connected: bool | None = None
    github_connected: bool | None = None
    slack_connected: bool | None = None
    db_connected: bool | None = None
    hf_configured: bool | None = None


@app.get("/platform/users/{user_id}/integrations")
def get_integrations(user_id: str, caller: dict = Depends(require_self_or_admin)):
    res = (
        supabase.table("integrations").select("*").eq("user_id", user_id).single().execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="No integrations row for this user")
    return res.data


@app.post("/platform/users/{user_id}/integrations")
def update_integrations(
    user_id: str, body: IntegrationsBody, caller: dict = Depends(require_self_or_admin)
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    res = supabase.table("integrations").update(updates).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No integrations row for this user")
    return res.data[0]


# ── Admin ─────────────────────────────────────────────────────────────────

@app.get("/platform/admin/users")
def list_users(caller: dict = Depends(require_admin)):
    res = supabase.table("profiles").select("*").execute()
    return res.data


# ── HuggingFace Space verification ──────────────────────────────────────

class VerifyHfSpaceBody(BaseModel):
    url: str


@app.post("/platform/verify-hf-space")
async def verify_hf_space(body: VerifyHfSpaceBody, caller: dict = Depends(require_user)):
    parsed = urlparse(body.url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise HTTPException(status_code=400, detail="URL must be an https:// HuggingFace Space URL")
    if not any(parsed.hostname.endswith(suffix) for suffix in ALLOWED_HF_HOST_SUFFIXES):
        raise HTTPException(status_code=400, detail="URL must point to a huggingface.co / hf.space host")

    health_url = f"{parsed.scheme}://{parsed.netloc}/health"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(health_url)
        ok = resp.status_code == 200 and resp.json().get("status") == "ok"
        return {"ok": ok, "status_code": resp.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Agent provisioning ───────────────────────────────────────────────────

class ProvisionRequest(BaseModel):
    user_id: str
    project_name: str


@app.post("/platform/provision-agent")
async def provision_agent(req: ProvisionRequest, caller: dict = Depends(require_user)):
    _require_self_or_admin_for(req.user_id, caller)

    user_id = req.user_id
    # Generate a short unique space name
    short_id = user_id.replace("-", "")[:8]
    space_name = f"zestqa-{short_id}"

    try:
        # Step 1 — Create HuggingFace Space
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://huggingface.co/api/repos/create",
                headers={
                    "Authorization": f"Bearer {HF_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "type": "space",
                    "name": space_name,
                    "private": False,
                    "sdk": "docker",
                    "exist_ok": True,
                },
            )

        hf_space_url = f"https://{HF_USERNAME}-{space_name}.hf.space"

        # Step 2 — Create Vercel project
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.vercel.com/v9/projects",
                headers={
                    "Authorization": f"Bearer {VERCEL_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "name": space_name,
                    "framework": None,
                    "rootDirectory": "dashboard/frontend",
                    "gitRepository": {
                        "type": "github",
                        "repo": "SarymSikander/zestqa-agent",
                    },
                    "environmentVariables": [
                        {
                            "key": "CLOUD_API",
                            "value": hf_space_url,
                            "target": ["production"],
                        }
                    ],
                },
            )

        dashboard_url = f"https://{space_name}.vercel.app"

        # Step 3 — Save to Supabase
        supabase.table("profiles").update({
            "hf_space_url": hf_space_url,
            "dashboard_url": dashboard_url,
        }).eq("id", user_id).execute()

        return {
            "hf_space_url": hf_space_url,
            "dashboard_url": dashboard_url,
            "status": "provisioned",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
