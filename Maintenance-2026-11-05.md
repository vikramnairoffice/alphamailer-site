# Maintenance - 2026-11-05

Remove unused imports; update Python dependencies; migrate lifespan/templates and bcrypt compatibility; regenerate schemas.

## Validation

Full suite: 64 passed, 1 skipped. Added password/login/template compatibility suite: 5 passed. Isolated test database; no provider effects.

## Compatibility

Stable releases were checked on 2026-11-05. JavaScript projects require Node
26.13.0 or newer. Desktop Gradio uses Pillow 12.3.0 because it requires Pillow
below 13. Android retains vendor-native Pillow 11.0.0, cryptography 42.0.8,
lxml 5.3.0 and cffi 1.17.1. Flutter transitive constraints are retained.
The Windows embedded Python builder stays on supported 3.13.17.

This maintenance does not establish device, provider or release acceptance.
