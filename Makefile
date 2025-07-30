IMAGE := ghcr.io/ministryofjustice/tech-docs-github-pages-publisher@sha256:30d00879b5c82afa5d76264164db46189fa11d4358b37ca35b6a62e341d62bb7 # v5.1.0

# Use this to run a local instance of the documentation site, while editing
.PHONY: preview check

review-docs:
	python3 -m bin.document_review_checker

preview:
	docker run -it --rm \
	    --name tech-docs-github-pages-publisher-preview \
	    --volume $(PWD)/config:/tech-docs-github-pages-publisher/config \
		--volume $(PWD)/source:/tech-docs-github-pages-publisher/source \
		--publish 4567:4567 \
		$(IMAGE)/usr/local/bin/preview

deploy:
	docker run --rm \
		-v $$(pwd)/config:/app/config \
		-v $$(pwd)/source:/app/source \
		-it $(IMAGE) /scripts/deploy.sh

check:
	docker run --rm \
		-v $$(pwd)/config:/app/config \
		-v $$(pwd)/source:/app/source \
		-it $(IMAGE) /scripts/check-url-links.sh

local-setup:
	brew install pre-commit && pre-commit install

redact-terraform-output:
	sed -e 's/AWS_SECRET_ACCESS_KEY".*/<REDACTED>/g' \
		-e 's/AWS_ACCESS_KEY_ID".*/<REDACTED>/g' \
		-e 's/$AWS_SECRET_ACCESS_KEY".*/<REDACTED>/g' \
		-e 's/$AWS_ACCESS_KEY_ID".*/<REDACTED>/g' \
		-e 's/\[id=.*\]/\[id=<REDACTED>\]/g' \
		-e 's/::[0-9]\{12\}:/::REDACTED:/g' \
		-e 's/:[0-9]\{12\}:/:REDACTED:/g'
