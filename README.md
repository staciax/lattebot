<p align="center">
  <img width="225" height="225" src="https://i.imgur.com/ufq5WOM.png">
</p>
<h3 align="center">lattebot</h5>
<h4 align="center">A cute little Discord bot, created during my fun and free moments.</h5>

## Introduction

Lattebot started as one of my first programming projects, created for a close group of friends who play games together. What started as a simple Discord bot has evolved through multiple versions (v1, v2, and more) to become the current iteration you see today. Each version represents a milestone in my programming journey, with improvements in code structure, features, and efficiency. This repository showcases not just a Discord bot, but also my growth as a developer from my early coding days to now.


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
