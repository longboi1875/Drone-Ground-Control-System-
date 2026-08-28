.PHONY: setup dev test check benchmark px4 px4-headless

setup:
	./scripts/setup.sh

dev:
	./scripts/dev.sh

test:
	.venv/bin/pytest -q
	npm test

check:
	.venv/bin/ruff check mission_service
	.venv/bin/mypy mission_service/skylink
	npm run lint
	npm run build

benchmark:
	.venv/bin/skylink-benchmark --commands 100

px4:
	./scripts/run_px4.sh

px4-headless:
	HEADLESS=1 ./scripts/run_px4.sh
