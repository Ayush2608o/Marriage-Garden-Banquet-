# Royal Venue

A polished, responsive wedding venue website built with Django. The first release includes the public venue experience, a saved enquiry flow, and a simple admin workspace for maintaining venue listings and following up with couples.

## Run locally

1. Install Python 3.10 or newer.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install the dependencies and create a local environment file:

   ```powershell
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

4. Prepare the database and create an admin login:

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. Start the development server at <http://127.0.0.1:8000/>:

   ```powershell
   python manage.py runserver 127.0.0.1:8000
   ```

Run `python manage.py test` to verify the application. The admin workspace is at `/admin/`. Enquiries are available in Django Admin under **Venues → Enquiries** and in the searchable owner dashboard at `/owner/`; the polling customer chat inbox is at `/owner/whatsapp/`. Website visitors can start a private, in-site chat from the **Chat with us** button; replies are saved in the inbox and appear in that visitor's browser session. This chat does not require WhatsApp Cloud API credentials. Run `python database/seed_data.py` for local demo records; it creates `venueowner` / `RoyalVenueDemo2026!` with admin access. Change or remove this demo account before using a shared or production environment.

Customer accounts use `/signup/` and `/signin/`; venue staff use `/admin/login/` for the operations Admin.

## Project structure

```text
config/              Django settings and entry points
apps/                Modular accounts, customers, venues, vendors, staff, bookings, quotations, payments, WhatsApp and audit apps
templates/            Shared shell and customer pages
database/             Local SQLite database and idempotent development seed script
static/css/           Responsive visual system
static/js/            Lightweight navigation and message interactions
media/                Local uploads (ignored by git)
```

The public imagery currently uses Unsplash image URLs and the typefaces load from Google Fonts. Replace them with licensed brand photography and self-hosted fonts before a production launch.

## Production setup

### Render + Netlify deploy

This project is a server-rendered Django site, so Netlify cannot run it as a static site on its own. The repository-root `render.yaml` provisions the Django web service, PostgreSQL database, and persistent media disk on Render. The repository-root `netlify.toml` proxies all Netlify paths to `https://royalvenue-web.onrender.com`, keeping the Netlify URL in the browser. If Render assigns a different service URL, update the proxy destination in `netlify.toml` before deploying Netlify.

1. Push the complete repository, including the top-level `render.yaml` and `netlify.toml`, to GitHub.
2. In Render, create a **Blueprint** from that repository and apply `render.yaml`. The blueprint uses paid Render resources for the database and persistent uploaded-media storage; review the plan and current price shown by Render before applying.
3. Wait for the `royalvenue-web` service deploy to succeed. Open its `onrender.com` URL directly once to confirm it responds.
4. In Netlify, import the same repository. Keep the repository root as the base directory and use the committed `netlify.toml`; no frontend build command is needed. Deploy the site.
5. Copy the final Netlify domain (and any custom domain) into Render's `CSRF_TRUSTED_ORIGINS` environment variable as comma-separated HTTPS origins, for example `https://*.netlify.app,https://royalvenue.example`. Also add any custom domain hostname (without `https://`) to `DJANGO_ALLOWED_HOSTS` if Render receives requests using that host. Save and redeploy the Render service.
6. Create the first administrator from the Render Shell with `python manage.py createsuperuser`; then sign in at `/admin/` on the Netlify URL.

Render's free Postgres databases expire after 30 days, so the included Blueprint selects a paid database plan to keep production records. The persistent disk stores files uploaded through Django Admin across deploys. Make a backup plan for important database and media data. Email and WhatsApp integrations remain optional and need their own credentials in Render environment settings. Never copy `.env` or production secrets into GitHub.

For manual deployment, set a unique `DJANGO_SECRET_KEY`, keep `DJANGO_DEBUG=False`, add production hostnames to `DJANGO_ALLOWED_HOSTS`, and set `CSRF_TRUSTED_ORIGINS` to comma-separated HTTPS origins. Set `DATABASE_URL` to PostgreSQL and `MEDIA_ROOT` to persistent storage. The included Render build script installs dependencies, runs `collectstatic`, and applies migrations. Configure SMTP using `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `ENQUIRY_NOTIFICATION_EMAIL`; configure the `WHATSAPP_*` variables to activate Meta Cloud API webhooks and replies. The inbox polls every four seconds.

## APIs

- `GET /api/venues/?city=Jaipur&venue_type=GARDEN`
- `GET /api/vendors/?city=Jaipur&category=PHOTOGRAPHER`
- `GET /api/staff/?available=true` (public phone numbers are masked)
- `GET /api/availability/?venue=1&date=2026-12-12&slot=FULL_DAY`
- `POST /api/bookings/` (authenticated)
- `POST /enquire/` (public event enquiry; returns `201` JSON and a reference ID when requested with `Accept: application/json`)
- `GET /api/whatsapp/webhook/` and `POST /api/whatsapp/webhook/` (Meta webhook)

Venue cards show each active venue's published capacity and discounted starting price (when configured). Selecting a venue's enquiry arrow pre-fills that venue on the enquiry form and stores the association with the enquiry; requests without a selected venue remain supported.

To verify enquiry persistence locally, submit the home-page form and note the confirmation reference. Sign in as a superuser at `/admin/` and open **Venues → Enquiries**, or sign in as an owner and open `/owner/`; the new pending enquiry is searchable by its name, email, phone, notes, venue or reference and can be marked confirmed/contacted, archived or deleted. Use **Print summary** for an enquiry or **Print details** for a booking to print or save a PDF from the browser. These are operational summaries, not invoices or final price quotes. Enquiry notifications are written to the server log; configure `ENQUIRY_NOTIFICATION_EMAIL` and the optional `EMAIL_*` settings in `.env` to send email notifications.

Public policies: `/privacy-policy/`, `/terms/`, and `/safety-policy/`.

## Next product phases

Payment gateway capture is intentionally represented as a provider-ready payment ledger; configure a payment provider before accepting online payments.
