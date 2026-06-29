# Local Development

Install Python dependencies:

```bash
python -m pip install -e ".[web,dev]"
```

Run tests:

```bash
pytest
```

Start the FastAPI backend:

```bash
uvicorn recordtree.web.api:app --host 127.0.0.1 --port 8000
```

Start the Vite frontend in another terminal:

```bash
cd web
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/api` requests to the backend.
