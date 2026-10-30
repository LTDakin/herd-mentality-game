# Herd Mentality

Small web server for playing the group card game Herd Mentality with friends on
the same wifi.

## Start (Docker, for a Raspberry Pi)

```sh
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"   # log out and back in after this

git clone https://github.com/LTDakin/herd-mentality-game.git
cd herd-mentality-game
docker compose up -d --build
```

Open `http://<pi-ip>:8000` from any device on the same wifi. Get the IP with
`hostname -I`.

Give the Pi a fixed IP (DHCP reservation in your router) so the
address friends type does not change.

## Start (without Docker)

```sh
sudo apt update && sudo apt install -y python3 git
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env

git clone https://github.com/LTDakin/herd-mentality-game.git
cd herd-mentality-game
uv run herd-mentality
```

Open `http://<pi-ip>:8000`. If a firewall is enabled: `sudo ufw allow 8000/tcp`.

## Play

1. Host opens `http://<host-ip>:8000`, logs in, ticks "wrangler".
2. Everyone else opens the same address and logs in with a unique name.
3. Wrangler hits start. Everyone has 30 seconds to answer the round's prompt;
   the scoreboard appears on its own when the clock runs out.
4. Wrangler hits next round, which deals a new prompt and a new 30 seconds.

## Development

```sh
uv run pytest
RELOAD=1 uv run herd-mentality
```
