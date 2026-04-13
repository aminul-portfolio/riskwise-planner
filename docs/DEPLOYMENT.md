# Deployment Notes

## Sprint 7 production basics
This project now supports:
- `STATIC_ROOT`
- WhiteNoise static serving
- Gunicorn process startup
- project-level `404.html` and `500.html`
- console logging for Django and `riskwise`

## Required environment variables
Set these in production:

- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS=your-domain.com`
- `CSRF_TRUSTED_ORIGINS=https://your-domain.com`
- `LOG_LEVEL=INFO`

## Static files
Run:

```bash
python manage.py collectstatic --noinput
```

## Session-storage limitation
RiskWise currently relies on session-backed dataset state for parts of the planning workflow.
That means:

- uploaded planning datasets are not persisted as a full platform data model
- very large uploads are not intended for long-lived multi-user production use yet
- resetting session state can remove the active planning context

This is acceptable for the portfolio/reviewer release, but it should be documented clearly until a persistent planning dataset model is introduced.

## What is still intentionally deferred
This Sprint 7 pass does **not** yet add:

- seed demo command
- structured logging calls inside every view/service function
- settings split into base/dev/prod modules

Those can be completed in the next Sprint 7 pass.
