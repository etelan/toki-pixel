# toki_pona

Tiny Toki Pona Pixoo sender.

## Build

From the repo root:

```bash
python3 -m pip install pillow pixoo
```

This folder now keeps its Python code, embedded glyphs, and default font inside `toki_pona/`.

## Commands

From this folder:

```bash
python3 random_once.py
python3 random_once.py --toki tonsi
python3 random_once.py --eng white
python3 random_once.py --reset
```

From the repo root:

```bash
python3 toki_pona/random_once.py
python3 toki_pona/random_once.py --toki tonsi
python3 toki_pona/random_once.py --eng white
python3 toki_pona/random_once.py --reset
```

`random_once.py` stores its no-repeat random state in `.random_cycle_state.json`.

## Raspberry Pi Zero W

Install system dependencies (needed for Pillow):

```bash
sudo apt-get install -y python3-pip libjpeg-dev zlib1g-dev libfreetype6-dev
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Then run as normal:

```bash
python3 random_once.py
```

To use from another Python script:

```python
from display import send_random, send_word

send_random()          # send a random word
send_word("toki")     # send a specific word
```