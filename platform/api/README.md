---
title: ZestQA Platform API
emoji: 🧪
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: "4.42.0"
pinned: false
---

# ZestQA Platform API

Backend API for ZestQA Agent platform. `main.py` defines the FastAPI app and
every `/health` / `/platform/*` route (see that file for the route list and
their Supabase-JWT auth requirements). `app.py` is the entrypoint HF Spaces
runs (`python app.py`, since there's no `app_file` override here to say
otherwise): it starts FastAPI with `uvicorn` on port 7860 in a background
thread, then launches a placeholder Gradio interface on port 7861 in the
main thread. The Gradio UI itself isn't the point — `demo.launch()` just
blocks so the process (and the daemon thread running FastAPI) stays alive;
the public Space URL is served by FastAPI on 7860.

## Deploying

Push only `platform/api/` to the `zestqa-platform` HuggingFace Space:

```bash
cd ~/Desktop/sqa-agent/platform/api
git add .
git commit -m "fix: run FastAPI in thread alongside Gradio to keep Space alive"
git push origin main --force
```

The `origin` remote here is already configured to push to that Space. Don't
paste the HF token into this file, a commit message, or a `git remote add`
command you keep around — it stays only in `origin`'s local git config (and
never gets committed).

Also commit to GitHub:

```bash
cd ~/Desktop/sqa-agent
git add platform/api/
git commit -m "fix: keep Space alive with Gradio thread"
git push origin main
```
