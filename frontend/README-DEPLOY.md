# フロントエンドデプロイガイド

このドキュメントはReactフロントエンドをAWSにデプロイする手順を説明します。

## 前提条件

- Node.js 18+ がインストールされていること
- AWS CLIがインストール・設定されていること
- S3バケットが作成されていること
- CloudFront Distribution が設定されていること（オプション）

## ビルド

```bash
cd frontend
npm install
npm run build
```

ビルド成果物は `dist/` ディレクトリに生成されます。

## デプロイ

### 1. 環境変数の設定

```bash
# .env.deploy.example をコピー
cp .env.deploy.example .env.deploy

# 環境に合わせて編集
# - AWS_REGION: AWSのリージョン
# - S3_BUCKET: フロントエンド用のS3バケット名
# - CLOUDFRONT_DISTRIBUTION_ID: CloudFront Distribution ID（オプション）
# - ENVIRONMENT: 環境 (dev/staging/prod)
```

### 2. デプロイスクリプトの実行権限設定

```bash
chmod +x frontend/scripts/deploy.sh
```

### 3. デプロイ実行

```bash
# 環境変数ファイルから設定を読み込んでデプロイ
source frontend/.env.deploy
frontend/scripts/deploy.sh
```

または、環境変数を指定して直接実行：

```bash
AWS_REGION=ap-northeast-1 \
S3_BUCKET=my-frontend-bucket \
CLOUDFRONT_DISTRIBUTION_ID=E1234567890ABC \
ENVIRONMENT=prod \
frontend/scripts/deploy.sh
```

## デプロイスクリプトの動作

デプロイスクリプト（`frontend/scripts/deploy.sh`）は以下の処理を実行します：

### 1. 環境変数チェック
必要な環境変数が設定されているかを確認します。

### 2. ビルド
`dist/` ディレクトリが存在しない場合、自動的にビルドを実行します。

### 3. S3へのアップロード
- **静的ファイル** （JS、CSS、画像など）
  - キャッシュ制御: `max-age=31536000` （1年）
  - `index.html` と `.map` ファイルは除外

- **index.html**
  - キャッシュ制御: `max-age=3600` （1時間）
  - HTMLファイルは短いキャッシュで常に最新版を配信

- **ソースマップ** （`.map` ファイル）
  - キャッシュ制御: `max-age=0` （キャッシュなし）
  - デバッグ用途のため最新版を保証

### 4. CloudFrontキャッシュ無効化（オプション）
`CLOUDFRONT_DISTRIBUTION_ID` が設定されている場合：
- CloudFront Distribution のキャッシュを全て無効化
- 無効化の完了まで待機

## キャッシュ戦略

このデプロイスクリプトは以下のキャッシュ戦略を実装しています：

| ファイル | キャッシュ期間 | 理由 |
|---------|--------------|------|
| JS/CSS/画像 | 1年 | ハッシュ名で一意性が保証されているため長期キャッシュ可能 |
| index.html | 1時間 | エントリーポイント、常に最新版の確認が必要 |
| ソースマップ | なし | デバッグ用、最新版を保証 |

## トラブルシューティング

### エラー: "AWS credentials not found"
AWS CLIが正しく設定されていません。以下を確認してください：

```bash
# AWS認証情報の確認
aws sts get-caller-identity

# または AWS CLIの設定
aws configure
```

### エラー: "Access Denied"
IAMユーザーに以下の権限がないか確認：
- `s3:PutObject`
- `s3:DeleteObject`
- `s3:ListBucket`
- `cloudfront:CreateInvalidation` （CloudFront使用時）
- `cloudfront:GetInvalidation` （CloudFront使用時）

### エラー: "S3 bucket does not exist"
S3バケットが存在しているか、正しい名前を指定しているか確認してください。

### CloudFrontキャッシュ無効化が失敗する
`CLOUDFRONT_DISTRIBUTION_ID` が正しいか確認してください：

```bash
# Distribution一覧を確認
aws cloudfront list-distributions --query 'DistributionList.Items[].{Id:Id,DomainName:DomainName}'
```

## 本番環境へのデプロイ

本番環境へのデプロイ時は以下を確認してください：

1. **環境変数が本番用に設定されている**
   ```bash
   ENVIRONMENT=prod
   S3_BUCKET=meal-management-frontend-prod
   ```

2. **ビルドが成功している**
   ```bash
   npm run build
   ```

3. **TypeScriptコンパイルエラーがない**
   ```bash
   npx tsc --noEmit
   ```

4. **E2Eテストが全て通っている**
   ```bash
   npm run test:e2e
   ```

## CI/CDパイプラインでの使用

GitHub ActionsなどのCI/CDパイプラインで使用する場合：

```yaml
- name: Deploy to AWS
  env:
    AWS_REGION: ap-northeast-1
    S3_BUCKET: meal-management-frontend-${{ matrix.environment }}
    CLOUDFRONT_DISTRIBUTION_ID: ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }}
    ENVIRONMENT: ${{ matrix.environment }}
  run: |
    chmod +x frontend/scripts/deploy.sh
    frontend/scripts/deploy.sh
```

## 参考資料

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [S3 Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
