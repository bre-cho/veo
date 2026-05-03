# 04 — Stripe Setup

Create products:

- Pro Poster Studio — $19/mo
- Agency System — $49/mo
- Empire Automation — $99/mo

Webhook endpoint:

```txt
https://yourdomain.com/api/stripe/webhook
```

Events:

```txt
checkout.session.completed
payment_intent.succeeded
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
```

ENV:

```env
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```
