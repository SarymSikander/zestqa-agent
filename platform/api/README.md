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

Backend API for ZestQA Agent platform. Runs as a plain FastAPI app — no
Gradio UI is mounted. `main.py` defines the FastAPI app and every
`/health` / `/platform/*` route (see that file for the route list and their
Supabase-JWT auth requirements). `app.py` is the entrypoint HF Spaces runs
(`python app.py`, since there's no `app_file` override here to say
otherwise): it imports `app` from `main.py` and starts it with `uvicorn`.

## Deploying

Push only `platform/api/` to the `zestqa-platform` HuggingFace Space:

```bash
cd ~/Desktop/sqa-agent/platform/api
git add .
git commit -m "fix: run FastAPI directly without gradio import"
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
git commit -m "fix: FastAPI without gradio"
git push origin main
```
