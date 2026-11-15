# Chainpiece

A collectibles registry with a tamper-evident custody ledger. Code arrives via pull request.

## Mistral chat app (minimal)

A minimal Next.js (App Router) + TypeScript + Tailwind web app with a simple chat interface. It calls the Mistral API with the official TypeScript SDK (`@mistralai/mistralai`) using the `mistral-small-latest` model. The `MISTRAL_API_KEY` is only ever read server-side, in `app/api/chat/route.ts` — it is never shipped to the browser.

### Setup

```bash
npm install
cp .env.example .env.local
```

Then edit `.env.local` and set your key from [console.mistral.ai](https://console.mistral.ai/):

```bash
MISTRAL_API_KEY=your_api_key_here
```

### Run locally

```bash
npm run dev
```

Open http://localhost:3000 and start chatting.

### Production build

```bash
npm run build
npm start
```
