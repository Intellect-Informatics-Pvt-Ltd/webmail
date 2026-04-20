.PHONY: openapi test lint

openapi:
	@echo "Exporting OpenAPI specification..."
	@python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json
	@echo "Written to openapi.json"

test:
	pytest --tb=short -q

lint:
	ruff check .

migrations-up:
	python -m migrations up

migrations-status:
	python -m migrations status
