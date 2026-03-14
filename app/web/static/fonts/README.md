Self-hosted Noto Sans KR webfont assets for consistent rendering across macOS/Linux deployments.

Source:
- https://fonts.google.com/noto/specimen/Noto+Sans+KR
- https://fonts.gstatic.com/s/notosanskr/

Notes:
- The app uses these files via `@font-face` in `app/web/static/css/app.css`.
- This avoids depending on OS-installed fonts, so Linux deployments render the same UI as local development.
