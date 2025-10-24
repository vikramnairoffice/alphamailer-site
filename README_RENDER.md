# Deploy URL Registry to Render (Free)

This repo includes a Render Blueprint (`render.yaml`) to deploy the FastAPI site with a free Postgres database.

## Prereqs
- A GitHub repo containing this code
- A Render account (free) at https://render.com

## One‑time setup (UI)
1. Push this repo to GitHub (make sure `render.yaml` is in the root).
2. In Render, click New → Blueprint.
3. Connect the GitHub repo and select it.
4. Fill required env vars when prompted:
   - `API_TOKEN` → your secret used by the app runners when posting URLs
   - `SESSION_SECRET` → any long random string
5. Click Apply; Render will provision:
   - `url-registry-db` (free Postgres)
   - `url-registry-admin` (FastAPI web service)

When it finishes, you’ll get a URL like `https://url-registry-admin.onrender.com`.

## Runners (Colab/Deepnote/Hugging Face)
Set these env vars when launching your mailer app so it posts the public URL:

```
URL_PUBLISH_WEBHOOK=https://url-registry-admin.onrender.com/api/instances
URL_PUBLISH_AUTH="Bearer <API_TOKEN>"
```

Sharing and publishing are ON by default in this repo.

## Optional CLI deployment
If you provide a Render API key, a blueprint can be triggered via API. Add an environment variable `RENDER_API_KEY` and I can run the API calls for you. Otherwise, the UI steps above are the quickest path.
