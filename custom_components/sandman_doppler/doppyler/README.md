# doppyler (bundled)

This folder contains a copy of `doppyler`, the Python library for the Sandman Doppler clock's local and cloud API, maintained as part of this integration.

- **Origin:** `pa-innovation/doppyler` at commit `3a3a545` (version `0.0.21b0`). That includes pa-innovation/doppyler#276 (always send `vol` with alarm sound requests and accept a plain-text `OK` reply) and pa-innovation/doppyler#277 (load `ZoneInfo` outside the event loop).
- **Why it's bundled:** the `doppyler` project on PyPI can't currently be published to. An upload of 0.0.21b0 was rejected because the PyPI account that owns the project has no verified email address. Version 0.0.20 is the last release there.
- **Authors:** Raman Gupta and Cameron Kellough (Palo Alto Innovation), with other contributors to `pa-innovation/doppyler`.
- **License:** GNU General Public License v3.0, the same as this integration (see the repository's `LICENSE`).
- **Changes since the copy:**
  - Reformatted with `black`.
  - Cloud requests verify TLS certificates; only the clock's local API skips verification (`verify_ssl=False`).
  - Request and response bodies are redacted (password, tokens, local key) before they're logged or attached to exceptions.

  Make further fixes here.

The integration imports it as a subpackage (`from .doppyler.client import DopplerClient`), so it is not installed from PyPI and its loggers live under `custom_components.sandman_doppler.doppyler`.
