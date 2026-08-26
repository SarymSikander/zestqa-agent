---
title: ZestQA Platform API
emoji: 🧪
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: "4.42.0"
app_file: app.py
pinned: false
---

# ZestQA Platform API

Backend API for ZestQA Agent platform. Runs as a FastAPI app on a Gradio
HuggingFace Space — `app.py` mounts a placeholder Gradio UI at `/ui` for the
Space's health check, while `/health` and every `/platform/*` route are
served by the underlying FastAPI app (see `app.py` for the route list and
their Supabase-JWT auth requirements).

## Deploying

Push only `platform/api/` to the `zestqa-platform` HuggingFace Space:

```bash
cd ~/Desktop/sqa-agent/platform/api
git add .
git commit -m "feat: ZestQA platform API on Gradio SDK"
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
git commit -m "feat: ZestQA platform API on Gradio SDK"
git push origin main
```
