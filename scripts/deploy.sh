#!/bin/bash

# 食事管理アプリケーション デプロイスクリプト

set -e

# 色の定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 環境の選択
ENVIRONMENT=${1:-dev}

if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}エラー: 無効な環境です。dev, staging, prod のいずれかを指定してください${NC}"
    echo "使用方法: ./scripts/deploy.sh [dev|staging|prod]"
    exit 1
fi

echo "=========================================="
echo "環境: $ENVIRONMENT"
echo "=========================================="

# テストの実行
echo -e "\n${YELLOW}テストを実行中...${NC}"
pytest tests/ -v
echo -e "${GREEN}✓ すべてのテストが成功しました${NC}"

# Terraform planの実行
echo -e "\n${YELLOW}Terraform planを実行中...${NC}"
cd terraform
terraform plan -var="environment=$ENVIRONMENT" -out=tfplan
echo -e "${GREEN}✓ Terraform plan完了${NC}"

# デプロイの確認
echo -e "\n${YELLOW}上記の変更を適用しますか？ (yes/no)${NC}"
read -r response

if [[ "$response" != "yes" ]]; then
    echo -e "${RED}デプロイをキャンセルしました${NC}"
    rm -f tfplan
    exit 0
fi

# Terraform applyの実行
echo -e "\n${YELLOW}インフラをデプロイ中...${NC}"
terraform apply tfplan
rm -f tfplan
echo -e "${GREEN}✓ デプロイ完了${NC}"

cd ..

echo -e "\n${GREEN}=========================================="
echo "デプロイが正常に完了しました！"
echo "==========================================${NC}"
