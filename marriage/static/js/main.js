document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.nav');

  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!open));
      toggle.setAttribute('aria-label', open ? 'Open navigation' : 'Close navigation');
      nav.classList.toggle('is-open', !open);
    });
    nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open navigation');
      nav.classList.remove('is-open');
    }));
  }

  document.querySelectorAll('.toast__close').forEach((button) => {
    button.addEventListener('click', () => button.closest('.toast')?.remove());
  });
  document.querySelectorAll('.toast').forEach((toast) => {
    window.setTimeout(() => toast.remove(), 7000);
  });

  const enquiryForm = document.querySelector('.enquiry-form');
  const enquiryResult = document.querySelector('#enquiry-result');
  if (enquiryForm && enquiryResult) {
    const venueInput = enquiryForm.querySelector('[name="venue"]');
    const venueSelection = document.querySelector('#enquiry-venue-selection');
    enquiryForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submit = enquiryForm.querySelector('button[type="submit"]');
      submit.disabled = true;
      enquiryResult.className = 'enquiry-result';
      enquiryResult.textContent = 'Sending your enquiry…';
      try {
        const response = await fetch(enquiryForm.action, {
          method: 'POST',
          body: new FormData(enquiryForm),
          headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        });
        const contentType = response.headers.get('content-type') || '';
        const data = contentType.includes('application/json') ? await response.json() : {};
        if (!response.ok) {
          const errors = Object.values(data.errors || {})
            .flatMap((fieldErrors) => fieldErrors.map((error) => error.message));
          const message = errors.join(' ') || data.message;
          throw new Error(message || (response.status === 403
            ? 'The security check expired. Refresh the page and try again.'
            : 'We could not send your enquiry. Please try again.'));
        }
        if (!data.reference_id || !data.message) {
          throw new Error('We could not verify the enquiry confirmation. Please contact our team.');
        }
        enquiryResult.classList.add('is-success');
        enquiryResult.textContent = `${data.message} Our team will be in touch shortly.`;
        enquiryForm.reset();
        venueInput.value = '';
        venueSelection.hidden = true;
        venueSelection.textContent = '';
      } catch (error) {
        enquiryResult.classList.add('is-error');
        enquiryResult.textContent = error.message || 'We could not send your enquiry. Please try again.';
      } finally {
        submit.disabled = false;
      }
    });
  }
});
