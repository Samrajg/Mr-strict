# Mr.Strict — Frontend (Vercel)

Next.js React frontend for Mr.Strict AI Assignment Evaluator.

## Deployment to Vercel

1. In the Vercel Dashboard, import this repository.
2. Set the **Root Directory** to `frontend`.
3. Add the environment variable:
   - `NEXT_PUBLIC_API_BASE_URL`: Your deployed Render backend URL (e.g. `https://mr-strict-api.onrender.com`).
4. Click **Deploy**.

## Local Development

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.
