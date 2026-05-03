# 01 — Setup Local

```bash
npm install
npm run dev
```

Open:

```txt
http://localhost:3000
http://localhost:3000/studio
http://localhost:3000/editor
http://localhost:3000/marketplace
```

Test V6:

```bash
curl -X POST http://localhost:3000/api/v6/run \
  -H "Content-Type: application/json" \
  -d '{"text":"Tôi bán serum trị mụn","product":"Serum trị mụn","goal":"sale","industry":"Beauty"}'
```
