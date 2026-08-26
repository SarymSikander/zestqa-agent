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
otherwise): it just calls `uvicorn.run(app, host="0.0.0.0", port=7860)`
directly — no Gradio involved. That call already blocks until the server
stops, which is what keeps the Space's process alive; nothing extra is
needed for that. The Space still declares `sdk: gradio` in the frontmatter
below, but that only picks which base build environment HF uses — it
doesn't require the app itself to import or use `gradio`.

## Deploying

Push only `platform/api/` to the `zestqa-platform` HuggingFace Space:

```bash
cd ~/Desktop/sqa-agent/platform/api
git add .
git commit -m "fix: drop gradio, run uvicorn directly"
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
git commit -m "fix: drop gradio for platform API"
git push origin main
```
