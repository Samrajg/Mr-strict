# Mr.Strict — Backend API (Render)

Flask + SentenceTransformers Python REST API for assignment evaluation.

## Deployment to Render

1. Create a new **Web Service** on Render connected to this repository.
2. Set **Root Directory** to `backend`.
3. Set **Runtime** to `Python 3`.
4. Set **Build Command**:
   ```bash
   pip install -r requirements.txt
   ```
5. Set **Start Command**:
   ```bash
   gunicorn -b 0.0.0.0:$PORT run:app --timeout 120 --workers 1 --threads 4
   ```
6. Add Environment Variables:
   - `SECRET_KEY`: High-entropy random production secret string.
   - `FLASK_ENV`: `production`

## Local Development

```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python run.py
```
