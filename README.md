<p align="center">
  <img width="225" height="225" src="https://i.imgur.com/ufq5WOM.png">
</p>
<h3 align="center">lattebot</h5>
<h4 align="center">A cute little Discord bot, created during my fun and free moments.</h5>


## Requirements

- [Python](https://www.python.org) 3.13 or higher
- [uv](https://docs.astral.sh/uv) Python package and project manager.

## Installation

```bash
uv sync
```

## Configuration

1. Copy the `.env.example` file to `.env` and fill in the required values.

```
cp .env.example .env
```

2. Create a new Discord application and bot at the [Discord Developer Portal](https://discord.com/developers/applications).
3. Set up the required environment variables in the `.env` file
4. Set up the database by running the following command:
5. Sync application commands by running the following command:

```bash
uv run python pre_start.py
```

6. Start the bot by running the following command:

```bash
uv run python launcher.py
```

## License

This project is licensed under the GNUv3 License - see the [LICENSE](LICENSE.md) file for details.
