# AWS Device Farm ユースケースガイド

## 概要

このドキュメントでは、AWS Device Farm の適切なユースケースと、本プロジェクトでの設定変更の背景を記録します。

## 本プロジェクトでの問題点（2025-12-11）

### AWS からの警告

AWS から以下の警告メールを受信：

> We are reaching out about several recent errors your AWS account has experienced using the AWS Device Farm service. It seems that there may be an unsupported configuration being used as part of your test spec file for iOS.

### 問題の原因

**Web アプリに対して iOS 実機テストを実行していた**ことが原因です。

| 設定項目 | 問題のあった設定 | 修正後 |
|---------|------------------|--------|
| device-pool | `[android, ios]` | Android のみ |
| testspec.yml | `ios_test_host: macos_sequoia` | 使用せず |

### なぜ不適切だったか

1. **本プロジェクトは React Web アプリ**
   - Playwright + Chromium でのブラウザテストが目的
   - iOS Safari でのテストは Playwright の Webkit プロジェクトで代替可能

2. **Device Farm の iOS テストは過剰**
   - iOS 実機が必要なのはネイティブ機能（カメラ、GPS 等）のテスト
   - Web アプリのブラウザテストには不要
   - コストと実行時間が増加するだけ

3. **LIFF 環境のテストは Device Farm では不可能**
   - LINE アプリ内ブラウザは Device Farm でエミュレートできない
   - LIFF テストは手動または LIFF SDK モックで対応

## AWS Device Farm の適切なユースケース

### Device Farm が最適なケース

| ユースケース | 理由 |
|-------------|------|
| ネイティブアプリ (iOS/Android) | 実機でしかテストできない機能（カメラ、GPS、センサー） |
| ハイブリッドアプリ (React Native, Flutter) | ネイティブブリッジの動作確認 |
| 複数デバイス互換性テスト | iPhone 12/13/14、Galaxy S21/S22 等の差異検証 |
| App Store/Play Store 申請前 | 審査リジェクト回避のための実機検証 |
| パフォーマンステスト | 実機での CPU/メモリ使用量計測 |

### Device Farm が不要なケース

| ユースケース | 代替手段 |
|-------------|----------|
| 純粋な Web アプリ | Playwright / Cypress（ヘッドレスブラウザで十分） |
| API テスト | pytest / Jest |
| ビジュアルリグレッション | Percy / Chromatic |
| CI/CD パイプライン | GitHub Actions + Playwright |

## 本プロジェクトの推奨構成

### 変更前（過剰）

```
GitHub Actions
 ├─ Build frontend
 └─ Upload to Device Farm
      ├─ Android デバイス（実機） ← Web テストには過剰
      └─ iOS デバイス（実機）    ← 不要・エラーの原因
```

### 変更後（適切）

```
GitHub Actions
 ├─ Build frontend
 └─ Device Farm (Android のみ)
      └─ Android デバイス（実機）
```

### 将来の推奨構成

Device Farm を完全に廃止し、GitHub Actions 上での Playwright テストのみに移行することを推奨：

```
GitHub Actions
 ├─ Build frontend
 ├─ Playwright テスト（Chromium/Firefox/Webkit）
 └─ Deploy to CloudFront
```

**理由:**
- Web アプリには実機テストは不要
- GitHub Actions での Playwright テストで十分なカバレッジ
- コスト削減（Device Farm は分単位課金）
- 実行時間短縮（Device Farm は数十分かかる）

## LIFF 環境のテスト戦略

LIFF（LINE 内ブラウザ）環境は Device Farm ではテストできません。

| テスト種別 | 方法 |
|-----------|------|
| 単体テスト | Jest + LIFF SDK モック |
| E2E テスト（通常ブラウザ） | Playwright |
| E2E テスト（LIFF 環境） | 手動テスト |

### LIFF モックの例

```typescript
// tests/mocks/liff.ts
export const mockLiff = {
  init: jest.fn().mockResolvedValue(undefined),
  isLoggedIn: jest.fn().mockReturnValue(true),
  getProfile: jest.fn().mockResolvedValue({
    userId: 'test-user-id',
    displayName: 'Test User',
  }),
  getIDToken: jest.fn().mockReturnValue('mock-id-token'),
};
```

## 関連ファイル

- [.github/workflows/device-farm.yml](../.github/workflows/device-farm.yml) - Device Farm ワークフロー
- [frontend/testspec.yml](../frontend/testspec.yml) - Device Farm テスト仕様
- [frontend/playwright.config.ts](../frontend/playwright.config.ts) - Playwright 設定

## iOS テストホスト移行ガイド（公式ドキュメント要約）

iOS ネイティブ/ハイブリッドアプリのテストで Device Farm を使用する場合は、以下の移行ガイドを参照してください。

### 新しいテストホストの指定

```yaml
# testspec.yml
ios_test_host: macos_sequoia
```

### ソフトウェアバージョンの選択

**レガシーホストとの主な違い:**

| 項目 | レガシーホスト | 新ホスト |
|------|---------------|----------|
| バージョン管理 | nvm, pyenv, avm, rvm | `devicefarm-cli` に統一 |
| Appium | 1.x / 2.x | **2.x のみ** |
| Xcode | デバイス iOS バージョンに依存 | 全デバイスで同一バージョン利用可能 |
| libimobiledevice | 利用可能 | **削除**（devicectl に移行） |

**devicefarm-cli の使用例:**

```yaml
phases:
  install:
    commands:
      # Java 17 を選択
      - devicefarm-cli use java 17

      # Appium 2 を選択（1.x は非対応）
      - devicefarm-cli use appium 2
      - appium --version

      # Node.js バージョン指定
      - devicefarm-cli use node 18
```

### Appium 関連の変更点

1. **WebDriverAgent 環境変数の変更**
   - 旧: `DEVICEFARM_WDA_DERIVED_DATA_PATH_V*`
   - 新: `DEVICEFARM_APPIUM_WDA_DERIVED_DATA_PATH_V9`

2. **avm コマンドの廃止**
   ```yaml
   # 旧（使用不可）
   # - avm 2.3.1

   # 新
   - devicefarm-cli use appium 2
   ```

3. **Java ユーザー向け**
   - `$DEVICEFARM_TESTNG_JAR` 環境変数は廃止
   - 必要な JAR ファイルはテストパッケージに含める

### ファイルパスのベストプラクティス

- 絶対パスのハードコードは避ける
- 相対パスと環境変数を使用

```yaml
# 悪い例
- /Users/devicefarm/test/node_modules/.bin/appium

# 良い例
- npx appium
- $DEVICEFARM_LOG_DIR/appium.log
```

### iOS 17+ での devicectl

libimobiledevice が削除されたため、iOS 17 以上では Xcode の `devicectl` を使用：

```bash
# デバイス情報の取得
xcrun devicectl device info

# アプリのインストール
xcrun devicectl device install app --device <device-id> <app-path>
```

### 移行チェックリスト

iOS テストを Device Farm で実行する場合のチェックリスト：

- [ ] `ios_test_host: macos_sequoia` を指定
- [ ] nvm/pyenv/avm/rvm を `devicefarm-cli use` に置換
- [ ] Appium 2.x にアップグレード
- [ ] `DEVICEFARM_WDA_DERIVED_DATA_PATH_V*` を `DEVICEFARM_APPIUM_WDA_DERIVED_DATA_PATH_V9` に変更
- [ ] 絶対パスを相対パス/環境変数に変更
- [ ] libimobiledevice コマンドを devicectl に移行（iOS 17+）

## 参考リンク

- [AWS Device Farm Developer Guide](https://docs.aws.amazon.com/devicefarm/latest/developerguide/)
- [iOS Test Host Migration Guide](https://docs.aws.amazon.com/devicefarm/latest/developerguide/ios-host-migration.html)
- [Supported Software in Custom Test Environments](https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environments-software.html)
- [Environment Variables for Appium Tests](https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environments-envvars.html)
- [Playwright Documentation](https://playwright.dev/)

## 変更履歴

| 日付 | 変更内容 |
|------|----------|
| 2025-12-11 | 初版作成。iOS device pool を削除、Device Farm ユースケースを文書化 |
| 2025-12-11 | iOS テストホスト移行ガイド（公式ドキュメント要約）を追加 |
