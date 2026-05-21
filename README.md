# PythonNginx

Учебный упрощенный аналог nginx на Python: асинхронный HTTP-сервер со статикой,
keep-alive, virtual hosts, autoindex, open file cache, логированием и proxy_pass.

Главный документ по архитектуре и плану реализации: [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md).

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pynginx --config config/pynginx.conf
```

Пока это каркас проекта. Реализацию удобнее вести по чеклисту из гайда.
