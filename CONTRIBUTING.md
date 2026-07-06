# Contributing

Thanks for looking at Tinker Workbench.

## Good first contributions

- Dashboard UX ([live site](https://enaguthi.com/tinker-workbench/site/))
- `doctor` rules and messages
- `probe` alignment with [tinker#44](https://github.com/thinking-machines-lab/tinker/issues/44)
- Docs and examples
- Upstream design sketches in [docs/upstream-collab.md](docs/upstream-collab.md)

## Dev setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[local]" pytest ruff pyyaml
pytest tests/ -q
```

## Dashboard changes

1. Edit `site/app.js`, `site/dashboard.css`
2. `tinker-workbench export-dashboard latest`
3. Open `site/index.html` locally or run `./scripts/publish-site.sh`

## PRs

- Keep changes focused
- Run `pytest` and `ruff check`
- Link related upstream issues when relevant
