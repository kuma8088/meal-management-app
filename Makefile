.PHONY: help init plan apply destroy test clean

help:
	@echo "利用可能なコマンド:"
	@echo "  make init     - Terraformを初期化"
	@echo "  make plan     - Terraform planを実行"
	@echo "  make apply    - インフラをデプロイ"
	@echo "  make destroy  - インフラを削除"
	@echo "  make test     - テストを実行"
	@echo "  make clean    - 一時ファイルを削除"

init:
	cd terraform && terraform init

plan:
	cd terraform && terraform plan

apply:
	cd terraform && terraform apply

destroy:
	cd terraform && terraform destroy

test:
	pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
