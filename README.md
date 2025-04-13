<p align="center">
  <img width="225" height="225" src="https://i.imgur.com/ufq5WOM.png">
</p>
<h3 align="center">lattebot</h3>
<h4 align="center">A cute little Discord bot that grew alongside my coding skills.</h4>

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
4. Sync application commands by running the following command:

```bash
uv run python pre_start.py
```

5. Start the bot by running the following command:

```bash
uv run python launcher.py
```

## License

This project is licensed under the GNUv3 License - see the [LICENSE](LICENSE.md) file for details.

## Appreciation Note

A heartfelt thank you to all my friends in the Latte group on Discord. Without your support, encouragement, and the countless hours of gaming together, this project would never have come to life, and I might not have embarked on this journey to become a developer.

Our friendship, our shared memories of late-night gaming sessions, inside jokes, and all the chaotic moments we've experienced together have been the true inspiration behind lattebot from the very beginning.

Thanks for sticking with me through it all. You guys mean more to me than you probably realize. ✌️
