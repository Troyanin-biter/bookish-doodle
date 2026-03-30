# Deploy (Free Hosting)

## Option: Render (Worker, Free Plan)

1. Push this project to GitHub.
2. In Render, create a new Blueprint from the repository.
3. Render will read `render.yaml` automatically.
4. Set environment variable `BOT_TOKEN` in Render.
5. Deploy.

## Important

- The bot uses SQLite by default. On free hosts, filesystem can be ephemeral.
- If you need persistent data, connect an external database and migrate from SQLite.

