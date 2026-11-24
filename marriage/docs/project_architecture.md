# Project architecture

Royal Venue is a Django-rendered website. `config/` owns project settings and URL routing. `apps/venues/` owns venue catalogue and enquiry data. The homepage reads published venue listings, and enquiry submissions are stored as `Enquiry` records for the team to follow up through Django admin.

Templates share `templates/base.html`; the customer landing page is in `templates/customer/home.html`. The CSS and small progressive enhancement script live in `static/`. New business domains can be introduced as independent Django apps as the product expands.
