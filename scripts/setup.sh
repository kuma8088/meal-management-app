#!/bin/bash

# 食事管理アプリケーション セットアップスクリプト

set -e

echo "=========================================="
echo "食事管理アプリケーション セットアップ"
echo "=========================================="

# 色の定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 前提条件のチェック
echo -e "\n${YELLOW}前提条件をチェック中...${NC}"

# Terraformのチェック
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}エラー: Terraformがインストールされていません${NC}"
    echo "https://www.terraform.io/downloads からインストールしてください"
    exit 1
fi
echo -e "${GREEN}✓ Terraform: $(terraform version | head -n 1)${NC}"

# AWS CLIのチェック
if ! command -v aws &> /dev/null; then
    echo -e "${RED}エラー: AWS CLIがインストールされていません${NC}"
    echo "https://aws.amazon.com/cli/ からインストールしてください"
    exit 1
fi
echo -e "${GREEN}✓ AWS CLI: $(aws --version)${NC}"

# Pythonのチェック
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}エラー: Python 3がインストールされていません${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python: $(python3 --version)${NC}"

# Python依存関係のインストール
echo -e "\n${YELLOW}Python依存関係をインストール中...${NC}"
pip3 install -r requirements.txt
echo -e "${GREEN}✓ Python依存関係のインストール完了${NC}"

# Terraform設定ファイルの作成
echo -e "\n${YELLOW}Terraform設定ファイルを確認中...${NC}"
if [ ! -f "terraform/terraform.tfvars" ]; then
    echo -e "${YELLOW}terraform.tfvarsが見つかりません。サンプルからコピーします...${NC}"
    cp terraform/terraform.tfvars.example terraform/terraform.tfvars
    echo -e "${RED}重要: terraform/terraform.tfvars を編集して実際の値を設定してください${NC}"
else
    echo -e "${GREEN}✓ terraform.tfvars が存在します${NC}"
fi

# Terraformの初期化
echo -e "\n${YELLOW}Terraformを初期化中...${NC}"
cd terraform
terraform init
echo -e "${GREEN}✓ Terraform初期化完了${NC}"

# Terraformの検証
echo -e "\n${YELLOW}Terraform設定を検証中...${NC}"
terraform validate
echo -e "${GREEN}✓ Terraform設定は有効です${NC}"

cd ..

echo -e "\n${GREEN}=========================================="
echo "セットアップ完了！"
echo "==========================================${NC}"
echo ""
echo "次のステップ:"
echo "1. terraform/terraform.tfvars を編集して実際の値を設定"
echo "2. make plan でインフラ計画を確認"
echo "3. make apply でインフラをデプロイ"
echo ""
