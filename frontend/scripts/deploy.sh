#!/bin/bash

# フロントエンドデプロイスクリプト
# S3にビルド成果物をアップロードし、CloudFrontキャッシュを無効化

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 環境変数チェック
check_env() {
  local var_name=$1
  local var_value=${!var_name}

  if [ -z "$var_value" ]; then
    echo -e "${RED}エラー: 環境変数 $var_name が設定されていません${NC}"
    return 1
  fi
}

# 必要な環境変数をチェック
echo -e "${YELLOW}環境変数をチェック中...${NC}"
check_env "AWS_REGION" || exit 1
check_env "S3_BUCKET" || exit 1

# CloudFrontDISTRIBUTION_IDはオプション
if [ -z "$CLOUDFRONT_DISTRIBUTION_ID" ]; then
  echo -e "${YELLOW}警告: CloudFrontDISTRIBUTION_IDが設定されていません。キャッシュ無効化をスキップします${NC}"
  SKIP_CLOUDFRONT=true
fi

# 初期化
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/dist"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo -e "${GREEN}デプロイの開始${NC}"
echo "  プロジェクトディレクトリ: $PROJECT_DIR"
echo "  ビルドディレクトリ: $BUILD_DIR"
echo "  S3バケット: $S3_BUCKET"
echo "  AWS地域: $AWS_REGION"
echo "  環境: $ENVIRONMENT"
echo ""

# ビルド済みかチェック
if [ ! -d "$BUILD_DIR" ]; then
  echo -e "${YELLOW}ビルドを実行中...${NC}"
  cd "$PROJECT_DIR"
  npm run build
fi

if [ ! -f "$BUILD_DIR/index.html" ]; then
  echo -e "${RED}エラー: $BUILD_DIR/index.html が見つかりません${NC}"
  exit 1
fi

# S3へのアップロード
echo -e "${YELLOW}S3へのアップロード中...${NC}"

# 1. 静的ファイル（キャッシュ可能）をアップロード
aws s3 sync "$BUILD_DIR" "s3://$S3_BUCKET/" \
  --region "$AWS_REGION" \
  --delete \
  --cache-control "public, max-age=31536000" \
  --exclude "index.html" \
  --exclude "*.map" \
  || exit 1

echo -e "${GREEN}  静的ファイルをアップロードしました${NC}"

# 2. index.htmlをアップロード（キャッシュ短め）
aws s3 cp "$BUILD_DIR/index.html" "s3://$S3_BUCKET/index.html" \
  --region "$AWS_REGION" \
  --cache-control "public, max-age=3600" \
  --content-type "text/html; charset=utf-8" \
  || exit 1

echo -e "${GREEN}  index.htmlをアップロードしました${NC}"

# 3. ソースマップをアップロード（キャッシュなし）
if [ -f "$BUILD_DIR/assets"/*.map ]; then
  aws s3 sync "$BUILD_DIR/assets" "s3://$S3_BUCKET/assets/" \
    --region "$AWS_REGION" \
    --include "*.map" \
    --cache-control "private, max-age=0" \
    || echo -e "${YELLOW}  警告: ソースマップのアップロードに失敗しました${NC}"
fi

echo -e "${GREEN}S3へのアップロードが完了しました${NC}"

# CloudFrontキャッシュ無効化
if [ "$SKIP_CLOUDFRONT" != true ]; then
  echo -e "${YELLOW}CloudFrontキャッシュを無効化中...${NC}"

  INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text \
    || exit 1)

  echo -e "${GREEN}  無効化リクエストを送信しました (ID: $INVALIDATION_ID)${NC}"

  # 無効化の完了を待つ
  echo -e "${YELLOW}無効化の完了を待機中...${NC}"
  aws cloudfront wait invalidation-completed \
    --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" \
    --id "$INVALIDATION_ID" \
    || exit 1

  echo -e "${GREEN}CloudFrontキャッシュが無効化されました${NC}"
fi

echo ""
echo -e "${GREEN}デプロイが完了しました！${NC}"
echo "  S3バケット: s3://$S3_BUCKET/"

if [ "$SKIP_CLOUDFRONT" != true ]; then
  echo "  CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID"
fi
