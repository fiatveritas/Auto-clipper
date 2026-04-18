# Auto-Clipper — dev convenience commands
# Run `make` or `make help` for the list.
.PHONY: help install run reinstall test lint clean deploy-site

help:
	@echo "Auto-Clipper dev targets:"
	@echo "  make install    — run install.sh (fresh setup)"
	@echo "  make run        — launch the app"
	@echo "  make reinstall  — clean reinstall (preserves VODs)"
	@echo "  make test       — run the smoke test suite"
	@echo "  make lint       — run pyflakes + check shell script syntax"
	@echo "  make clean      — clear pyc + venv caches"
	@echo "  make deploy-site — wrangler-deploy the landing page"

install:
	./install.sh

run:
	./run.sh

reinstall:
	./reinstall.sh

test:
	python tests/test_smoke.py

lint:
	@echo "→ pyflakes"
	@python -m pyflakes analysis/*.py app.py clip_manager.py || true
	@echo "→ shell script syntax"
	@for f in install.sh run.sh reinstall.sh install-remote.sh Auto-Clipper.command; do \
		bash -n $$f && echo "  $$f OK" || echo "  $$f FAILED"; \
	done

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
	@echo "cleared pyc + __pycache__"

deploy-site:
	npx wrangler pages deploy site --project-name auto-clipper --branch main --commit-dirty=true
