# Contributing

Issues and pull requests are welcome.

## Development

1. Copy `.env.example` to `.env`.
2. Start the stack with `docker compose up -d --build`.
3. Open the frontend at `http://localhost:3000`.
4. Open the backend docs at `http://localhost:8000/api/docs`.

## Before Opening a PR

- Do not commit `.env`, local certificates, logs, backups, or personal screenshots.
- Keep changes scoped to the problem being solved.
- Run the frontend build:

```bash
cd frontend
npm run build
```

- If you change the database schema, add or update the Alembic migration.

## Pull Request Notes

- Describe the user-visible change.
- Mention any setup or migration steps required to test the change.
- If relevant, include screenshots with personal data removed.
