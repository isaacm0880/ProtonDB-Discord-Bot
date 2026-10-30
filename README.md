# ProtonDB Discord Bot

A Discord bot for checking **Linux/Proton game compatibility** and looking up useful **Steam game information** without leaving Discord.

Originally created for the [Playden PS5 project](https://github.com/leolobato/playden-ps5) community to make it easier to check Proton compatibility before trying Steam games through Playden. It also includes a few quality-of-life features for Steam game information.

**[Join the Playden Discord](https://discord.gg/wd8UjExpPA)**

> **Note:** ProtonDB reports reflect community experiences running games through Proton. They do **not** guarantee that a game will run on Playden or on a PS5. Hardware, drivers, runtime versions, and other platform differences can affect compatibility.

## Features

- Search for Steam games using slash-command autocomplete.
- Check ProtonDB compatibility tiers and community reports.
- View Steam store details, current regional pricing and Steam user-review ratings.
- Open separate **Requirements** and **Reviews** embeds using buttons.
- Read recent Steam game announcements.
- Look up games by Steam App ID.
- Docker-based deployment with configurable caching and Steam region/language.
- Consistent orange (`#B45D1F`) embeds.

## Commands

| Command | Description |
| --- | --- |
| `/protondb` | Search a game and view its ProtonDB compatibility tier, community reports and Linux-focused troubleshooting. |
| `/protondbid` | Look up ProtonDB compatibility using a Steam App ID. |
| `/steam` | Show Steam game details, rating, price and links. Use **Requirements** and **Reviews** buttons for additional information. |
| `/news` | Show recent Steam announcements for a game. |

Game-name commands support autocomplete. Some data may be unavailable if Steam or ProtonDB changes an endpoint, limits requests, or has no information for the selected game.

## Invite or self-host

The bot was created for the Playden community. To use a hosted instance in another Discord server, an invite link must be provided by the bot owner; a public invite is not currently listed here.

You can also host your own instance using Docker.

### Requirements

- Docker Engine and Docker Compose plugin
- A Discord application with a bot token
- Outbound internet access to Discord, Steam and ProtonDB

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/isaacm0880/ProtonDB-Discord-Bot.git
   cd ProtonDB-Discord-Bot
   ```

2. Create `.env` in the project directory:

   ```env
   DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
   DISCORD_GUILD_ID=
   CACHE_SECONDS=900
   LOG_LEVEL=INFO
   STEAM_COUNTRY=gb
   STEAM_LANGUAGE=english
   ```

   `DISCORD_GUILD_ID` is optional. Set it to a test server ID for faster slash-command registration during development; leave it empty for global commands. `STEAM_COUNTRY` defaults to `gb` and `STEAM_LANGUAGE` defaults to `english`. You can also set `HTTP_TIMEOUT_SECONDS` (default `12`).

3. In the [Discord Developer Portal](https://discord.com/developers/applications), enable the bot for your application and invite it to your server with the `bot` and `applications.commands` scopes. The bot uses slash commands and does not need privileged message-content intent.

4. Start the bot:

   ```bash
   docker compose up -d --build
   ```

5. View logs:

   ```bash
   docker compose logs -f
   ```

### Updating

```bash
git pull
docker compose up -d --build
```

Keep your `.env` private and never commit your Discord token. If you replace project files manually, **preserve your existing `.env`**.

### Troubleshooting

- **Bot offline:** Check the container logs and verify `DISCORD_TOKEN`.
- **Slash commands missing:** Check the application's invite scopes. Global command updates can take time to appear.
- **Missing game data:** Some Steam titles have no public price, requirements, reviews or announcements. ProtonDB individual-report retrieval relies on public data that can change.
- **Unexpected errors:** Review `docker compose logs -f` and open a GitHub issue with non-sensitive logs and steps to reproduce.

## Contributing

Issues and pull requests are welcome. When reporting a bug, include the command, Steam App ID, expected behaviour, actual behaviour and relevant logs. **Remove tokens, credentials and other sensitive information before posting logs.**

## Credits and acknowledgements

- [Playden PS5](https://github.com/leolobato/playden-ps5) — the community this bot was originally built to support.
- [ProtonDB](https://www.protondb.com/) — community Proton compatibility reports.
- [Steam](https://store.steampowered.com/) — game information, reviews, pricing and news.
- [discord.py](https://discordpy.readthedocs.io/) — Discord bot framework.

This is an independent community project and is not officially affiliated with Valve, Steam, ProtonDB or the Playden project.

## License

Released under the [MIT License](LICENSE).
