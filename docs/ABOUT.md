# Foodie Robot

## Inspiration

Food ordering apps hand you a menu and leave you guessing — *will this fit my fitness goals? is this too many
calories?* FoodieRobot flips that around: it recommends meals tailored to your
fitness goals and lets you order them directly, so it eliminates the guesswork.

And it lives where you already are — **WhatsApp**. No new app, no new account.
You just text it like a friend who knows every restaurant in town — *"something
light and high-protein for around ₦3000"* — and it tells you exactly what to
eat and lets you order it on the spot.

## What it does

- Chat with the bot on WhatsApp in plain language.
- It recommends meals tailored to your fitness goals, taste, budget, and time of
  day — and you order them directly, no guesswork.
- It can analyze a meal photo to estimate calories and nutrition.
- It handles the full flow — location, ordering, payments, referrals, and balances.

## How I built it

- **Backend:** Django (ASGI / Daphne) with a Huey worker for background jobs,
  PostgreSQL + PostGIS for data and geo, and Redis for caching and the task queue.
- **AI:** Alibaba Cloud's **Qwen** models via Model Studio (DashScope), used in
  three ways:
  - `qwen-max` for chat and **tool calling** — the bot decides which action to
    run (recommend, order, save location, etc.).
  - `qwen-vl-max` for **vision** — reading a meal photo.
  - `text-embedding-v4` for **embeddings** — turning meals and requests into
    vectors so I can match them by meaning.
- **Hosting:** Docker containers on Alibaba Cloud (ECS), with managed RDS
  (PostgreSQL) and Redis.

## Challenges I ran into

- **Structured output from vision.** Getting reliable, schema-shaped JSON out of
  the image analysis took prompt tuning plus a forgiving parser (handling code
  fences and stray text) so a single odd response wouldn't break the flow.
- **Embedding dimensions.** My database assumed 1536-dim vectors, so I pinned
  the embedding size to keep everything consistent.
- **Server-side image fetching.** The vision model downloads image URLs itself,
  so images must be hosted somewhere reliably reachable — I use a global CDN
  (Cloudinary) for that.
- **Keeping costs low.** Caching embeddings and filtering tools before each call
  kept token usage (and the bill) small.

## Accomplishments that I'm proud of

- **A bot that feels natural.** Tool calling lets it understand free-form
  requests and take real actions — no rigid menus or button trees.
- **Recommendations that actually fit you.** Semantic matching on fitness goals,
  taste, and budget turns "what should I eat?" into a direct answer you can order.
- **Full end-to-end flow on WhatsApp.** From recommendation to location to
  payment to referrals — all inside a chat, with no extra app to install.
- **Lean and cost-efficient.** Cached embeddings and pre-call tool filtering keep
  it fast and cheap to run.

## What I learned

- **Tool calling beats menus.** Letting the model pick the right action from a
  set of well-described tools made the bot feel natural instead of scripted.
- **Embeddings make search feel smart.** A little linear algebra goes a long
  way — semantic matching is far better than keyword matching for food.
- **Qwen is genuinely capable** across chat, vision, and embeddings, and one
  API key covers all three.

## What's next for Foodie Robot

- Scale to more regions. Currently it is based in Lagos, Nigeria.
- Smarter personalization as more taste signals accumulate.
- Multi-language support so the bot can chat the way each user does.
