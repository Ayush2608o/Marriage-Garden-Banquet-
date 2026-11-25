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

### Free Render + Netlify deploy

The Django app runs on Render and uses the existing `marriagedb` Free Postgres service; `render.yaml` defines the app and database association. After the Render web service is healthy, configure the repository-root `netlify.toml` to proxy requests to its `onrender.com` hostname so the existing Netlify domain serves the full Django app.

The Free plan is for testing, not production. Render Free Postgres is limited to 1 GB, has no backups, and expires 30 days after creation; data is deleted after the additional 14-day recovery window unless upgraded. Free web services sleep after 15 minutes without traffic, take about a minute to wake, and have an ephemeral filesystem. Uploaded files are not durable, and outbound SMTP ports are blocked. Check the current Render limits before accepting real bookings or storing customer records.

The Render build runs migrations against Postgres but does not import local SQLite records. Never commit `.env`, SQLite databases, customer records, chat messages, or production secrets to GitHub.

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
