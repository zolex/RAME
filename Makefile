.PHONY: build help
.DEFAULT_GOAL:=help

build: clean ## Build to folder
	pyinstaller RAME.spec

build1: clean ## Build to single file
	pyinstaller RAMEOneFile.spec

clean:
	rm -rf ./build

help: ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
