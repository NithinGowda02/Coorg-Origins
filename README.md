# Coorg Origins

A Flask e-commerce application for authentic products from Coorg (Kodagu), Karnataka.

## Current status

Phase 1 established the Flask application factory, environment-based configuration, extension registry, starter homepage, and health endpoint.

Phase 2 added PostgreSQL-ready SQLAlchemy configuration, the core catalog/order schema, and Flask-Migrate support. The schema includes users, categories, products, product images, product variants, carts, orders, order items, and payments.

Phase 3 added Flask-Login authentication, admin-role authorization, protected admin routing, CSRF-protected login/logout, and interactive administrator provisioning.

Phase 4 added the responsive admin dashboard shell with live product, category, low-stock, and payment-review metrics.

Phase 5 adds database-backed category management: listing, creation, editing, slug validation, and safe activation/deactivation from the admin area.

Phases 6 and 7 add product management and variant inventory: product creation/editing, category assignment, featured and active states, validated image uploads, multiple variants, SKU uniqueness, per-variant pricing, and stock quantities.

Phases 8 and 9 add the customer storefront: a dynamic Coorg-focused homepage, featured products, category browsing, a searchable shop, category filtering, sorting, pagination, responsive product cards, and active-stock filtering.

Phases 10 and 11 are represented by the customer homepage and shop catalog, including responsive browsing and storefront filtering.

Phase 12 adds product detail pages with image galleries, active variant selection, live price and stock display, product information, shipping notes, and related products.

Phase 13 adds a guest session cart with variant-aware quantities, stock checks, updates, and removal.

Phase 14 adds checkout and transactional order creation. Stock is locked and rechecked at checkout, order item prices are snapshotted, and the cart is cleared only after a successful commit.

Phase 15 adds UPI QR payment instructions. The QR payload includes the configured UPI ID and order amount, while every payment remains `pending_verification` until an administrator verifies the submitted transaction reference.

Phase 16 adds admin order operations: order listing, customer and item detail views, fulfilment status changes, and guarded payment verification with verifier and timestamp tracking.

Phase 17 completes responsive layouts across storefront, cart, checkout, payment, and admin order views.

Phase 18 adds lightweight motion: observer-based section reveals, restrained hero particles, staggered product cards, and `prefers-reduced-motion` support.

Phase 19 hardens configuration, secure cookies, upload limits, error handling, and admin boundaries.

Phase 20 adds canonical metadata, `sitemap.xml`, and `robots.txt`.

Phase 21 adds pytest coverage for catalog browsing, SEO routes, admin access, cart, checkout, and inventory reduction.

Phase 22 adds production configuration selection and deployment guidance below.

## Test

```powershell
py -m pytest
```

## Production run

Set `FLASK_ENV=production`, a strong `SECRET_KEY`, `DATABASE_URL`, and `UPI_ID`. Apply migrations before starting the WSGI server:

```powershell
$env:FLASK_ENV="production"
py -m flask --app run.py db upgrade
waitress-serve --call run:app
```

Use HTTPS in production so secure cookies work correctly, and store uploaded images on managed object storage when the application grows beyond a single server.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
py run.py
```

Open <http://127.0.0.1:5000> in a browser. The health endpoint is available at <http://127.0.0.1:5000/healthz>.

`DATABASE_URL` can remain empty during local development. The application then uses a local SQLite database file. For PostgreSQL, set a value such as:

```text
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/coorg_flavour
```

Set `UPI_ID` in `.env` before using the payment flow:

```text
UPI_ID=your-business@upi
```

An administrator can upload or replace the customer-facing merchant QR from **Admin → Payment QR**. The image is stored under `app/static/uploads/payment/` and served on payment pages; if no image has been uploaded, the app continues generating a per-order QR from `UPI_ID`.

Configure SMTP in `.env` to email customers when an order is placed or its status changes. `MAIL_DEFAULT_SENDER` should be an address accepted by your SMTP provider. Leave `MAIL_USERNAME` and `MAIL_PASSWORD` empty only if the server permits unauthenticated SMTP. If SMTP is not configured or sending fails, order changes still save and the failure is logged.

```text
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-smtp-username
MAIL_PASSWORD=your-smtp-password
MAIL_DEFAULT_SENDER=orders@example.com
```

Database migration commands:

```powershell
py -m flask --app run.py db migrate -m "describe the schema change"
py -m flask --app run.py db upgrade
```

Create the first administrator interactively. The password is entered at the terminal and is stored only as a hash:

```powershell
py -m flask --app run.py create-admin
```

Then open <http://127.0.0.1:5000/auth/login> and sign in. The protected dashboard is available at <http://127.0.0.1:5000/admin/>.
