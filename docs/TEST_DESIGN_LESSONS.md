# テスト設計の教訓

## 概要

本ドキュメントでは、食事管理アプリケーションの開発中に発見されたテスト設計上の問題点と、今後の設計における対策をまとめる。

## 発見された問題

### 1. ローカルテストと本番環境の乖離

#### 問題の詳細

ユニットテストと統合テストが「成功」しているにも関わらず、本番環境（AWS dev）で以下の重大な問題が発見された：

| 問題 | 原因 | 影響 |
|------|------|------|
| Lambda ZIP ファイルの破損 | パッケージングスクリプトの `cd` コマンドがワーキングディレクトリを変更 | 関数が完全に動作しない |
| `requests` モジュール不足 | 依存関係がZIPに含まれていなかった | `ImportModuleError` |
| `error_response()` シグネチャ不一致 | 関数呼び出し方法と定義の不一致 | 500 Internal Server Error |
| API Gateway パラメータ解析 | `event['query']` vs `event['queryStringParameters']['query']` | 400 Bad Request |
| DynamoDBHelper インターフェース不一致 | PascalCase vs snake_case パラメータ名 | TypeError |

#### 根本原因

1. **モックの過剰使用**: ユニットテストでは DynamoDB、API Gateway などをモック化したため、実際のインターフェースの違いを検出できなかった

2. **統合テストの環境差異**: ローカルの統合テストは `localstack` やモックを使用し、実際のAWSサービスとの統合を検証していなかった

3. **E2Eテストの不完全さ**: E2Eテストはフロントエンドの動作確認が主で、APIレスポンスの詳細な検証が不足していた

4. **デプロイパイプラインの検証不足**: Lambda ZIPファイルのパッケージング後に中身を検証するステップがなかった

### 2. テスト環境と本番環境のコード実行パスの違い

```
ローカルテスト:
  Python → 直接関数呼び出し → モック化されたDynamoDB

本番環境:
  API Gateway → Lambda Runtime → Python → DynamoDBHelper → DynamoDB
```

テストでは中間レイヤー（API Gateway、Lambda Runtime）がスキップされるため、以下が検証されなかった：
- `event` オブジェクトの構造
- Lambda context の属性
- 環境変数の解決
- 依存関係のインポート

## 今後の対策

### 1. 本番相当の統合テスト環境の構築

```yaml
# 推奨: 実際のAWSサービスを使用した統合テスト
integration_test:
  environment:
    - 専用のdev/test AWS環境を使用
    - 本番と同じTerraformモジュールでプロビジョニング
  validation:
    - Lambda関数の直接呼び出し（aws lambda invoke）
    - API Gatewayエンドポイントへのリクエスト
```

### 2. 契約テスト（Contract Testing）の導入

```python
# DynamoDBHelper の契約をテストで明示的に検証
def test_dynamodb_helper_scan_interface():
    """DynamoDBHelper.scan() の呼び出しシグネチャを検証"""
    import inspect
    sig = inspect.signature(DynamoDBHelper.scan)
    params = list(sig.parameters.keys())

    # snake_case パラメータであることを検証
    assert 'filter_expression' in params
    assert 'expression_attribute_values' in params
    assert 'FilterExpression' not in params  # PascalCase は NG
```

### 3. デプロイ前検証の強化

```bash
# パッケージング後の検証スクリプト例
#!/bin/bash
verify_lambda_package() {
    local zip_file=$1
    local function_name=$2

    # ZIPファイルのサイズ検証
    size=$(stat -f%z "$zip_file")
    if [ "$size" -lt 10000 ]; then
        echo "ERROR: $function_name package is too small ($size bytes)"
        exit 1
    fi

    # 必須ファイルの存在確認
    if ! unzip -l "$zip_file" | grep -q "${function_name}/__init__.py"; then
        echo "ERROR: Missing ${function_name}/__init__.py"
        exit 1
    fi

    # 依存関係の確認
    if ! unzip -l "$zip_file" | grep -q "requests"; then
        echo "ERROR: Missing requests dependency"
        exit 1
    fi
}
```

### 4. Smoke Test の必須化

デプロイ直後に本番環境で実行する軽量テスト：

```python
# smoke_tests.py
def test_food_search_api():
    """デプロイ後に本番APIを直接テスト"""
    response = requests.get(
        f"{API_BASE_URL}/foods/search",
        params={"query": "テスト", "limit": 1},
        headers={"Authorization": f"Bearer {get_test_token()}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "foods" in data
    assert "count" in data
```

### 5. テストピラミッドの見直し

```
現状:
  ┌─────────────────┐
  │   E2E Tests     │ 少
  ├─────────────────┤
  │ Integration     │ 少（モック依存）
  ├─────────────────┤
  │   Unit Tests    │ 多
  └─────────────────┘

推奨:
  ┌─────────────────┐
  │   E2E Tests     │ 少
  ├─────────────────┤
  │ Integration     │ 中（実サービス使用）
  │ + Smoke Tests   │
  ├─────────────────┤
  │ Contract Tests  │ 中
  ├─────────────────┤
  │   Unit Tests    │ 多
  └─────────────────┘
```

## チェックリスト

### 新機能開発時

- [ ] ユニットテストでモックを使用する場合、実際のインターフェースと一致することを確認
- [ ] API Gatewayのイベント構造を正確に模倣
- [ ] 依存関係のインポートエラーをCI/CDで検出

### デプロイ前

- [ ] Lambda ZIPファイルのサイズと内容を検証
- [ ] 依存関係が正しく含まれていることを確認
- [ ] Terraformのplanで変更内容を確認

### デプロイ後

- [ ] Smoke Testで主要エンドポイントの動作確認
- [ ] CloudWatch Logsでエラーがないことを確認
- [ ] 本番環境での手動確認（最低1つのAPIコール）

## 関連ファイル

- [scripts/package_lambda.sh](../scripts/package_lambda.sh) - Lambda パッケージングスクリプト
- [src/lambda/common/response.py](../src/lambda/common/response.py) - 共通レスポンスヘルパー
- [src/lambda/common/dynamodb_helper.py](../src/lambda/common/dynamodb_helper.py) - DynamoDB ヘルパー

## 修正履歴

| 日付 | 問題 | 修正内容 |
|------|------|----------|
| 2025-12-06 | ZIPパッケージング破損 | サブシェルで`cd`コマンドを実行 |
| 2025-12-06 | requests モジュール不足 | 共通の requirements.txt を追加 |
| 2025-12-06 | error_response シグネチャ | 文字列とステータスコードの受け入れを追加 |
| 2025-12-06 | queryStringParameters | API Gateway形式のパラメータ解析に対応 |
| 2025-12-06 | DynamoDBHelper呼び出し | snake_case パラメータに統一 |
