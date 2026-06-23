.PHONY: build serve clean reseed deploy

# Generate the static site into dist/
build:
	python3 build.py

# Build, then serve locally
serve: build
	@echo "Serving at http://localhost:8048  (ctrl-c to stop)"
	@cd dist && python3 -m http.server 8048

# Remove build output
clean:
	rm -rf dist

# Re-derive the original (zh) text in data/ from the archived source.
# Preserves existing English translations and pointers.
reseed:
	python3 scripts/seed_from_source.py

# Build and publish to koan.ehrlich.dev
deploy:
	./deploy.sh
