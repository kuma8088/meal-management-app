#!/bin/bash

# Lambda関数をパッケージ化するスクリプト

set -e

# プロジェクトルートディレクトリ
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
SRC_DIR="$PROJECT_ROOT/src/lambda"

echo "Packaging Lambda functions..."

# distディレクトリを作成
mkdir -p "$DIST_DIR"

# Lambda関数のリスト
LAMBDA_FUNCTIONS=(
    "line_handler"
    "meal_registration"
    "food_search"
    "barcode_recognition"
    "nutrition_calculation"
    "bmr_tdee_calculation"
    "goal_management"
    "daily_summary"
    "user_profile_management"
    "food_master_import"
    "weekly_report"
    "test_user_management"
    "authorizer"
    "define_auth_challenge"
    "create_auth_challenge"
    "verify_auth_challenge"
    "post_confirmation"
    "liff_login"
)

# 各Lambda関数をパッケージ化
for func in "${LAMBDA_FUNCTIONS[@]}"; do
    # Lambda関数のディレクトリが存在しない場合はスキップ
    if [ ! -d "$SRC_DIR/$func" ]; then
        echo "⚠ Skipping $func (directory not found)"
        continue
    fi

    echo "Packaging $func..."

    # 一時ディレクトリを作成
    TMP_DIR=$(mktemp -d)

    # Lambda関数のコードをコピー
    cp -r "$SRC_DIR/$func" "$TMP_DIR/"

    # 共通ライブラリをコピー
    cp -r "$SRC_DIR/common" "$TMP_DIR/"

    # 共通の依存関係をインストール
    if [ -f "$SRC_DIR/requirements.txt" ]; then
        pip3 install -r "$SRC_DIR/requirements.txt" -t "$TMP_DIR" --quiet --platform manylinux2014_x86_64 --only-binary=:all: 2>/dev/null || \
        pip3 install -r "$SRC_DIR/requirements.txt" -t "$TMP_DIR" --quiet
    fi

    # 関数固有のrequirements.txtがあればインストール
    if [ -f "$SRC_DIR/$func/requirements.txt" ]; then
        pip3 install -r "$SRC_DIR/$func/requirements.txt" -t "$TMP_DIR" --quiet --platform manylinux2014_x86_64 --only-binary=:all: 2>/dev/null || \
        pip3 install -r "$SRC_DIR/$func/requirements.txt" -t "$TMP_DIR" --quiet
    fi

    # ZIPファイルを作成（サブシェルでディレクトリ変更）
    (cd "$TMP_DIR" && zip -r "$DIST_DIR/${func}.zip" . -q)

    # 一時ディレクトリを削除
    rm -rf "$TMP_DIR"

    echo "✓ $func packaged"
done

echo "All Lambda functions packaged successfully!"
