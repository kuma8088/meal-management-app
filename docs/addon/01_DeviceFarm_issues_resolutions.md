# AWS Device Farm GitHub Actions ワークフロー構築で遭遇した問題と解決策

## 概要

AWS Device Farm を使用した E2E テストの CI/CD パイプラインを構築する際に遭遇した問題とその解決策をまとめます。GitHub Actions から Device Farm API を呼び出す際の落とし穴と正しい設定方法を解説します。

## 環境情報

- **CI/CD**: GitHub Actions
- **テストフレームワーク**: Playwright
- **対象デバイス**: Android (Samsung, OS >= 11), iOS (Apple, OS >= 15)
- **AWS CLI**: 最新版（GitHub Actions ubuntu-latest）
- **リージョン**: us-west-2（Device Farm は特定リージョンのみ対応）

---

## 問題1: YAML 構文エラー - secrets 参照

### 問題

```yaml
if: secrets.SLACK_WEBHOOK_URL != ''
```

GitHub Actions の YAML で上記のように secrets を直接参照すると、以下のエラーが発生：

```
Unrecognized named-value: 'secrets'
```

### 原因

GitHub Actions の `if` 条件式では、secrets を直接参照できません。`${{ }}` 構文で囲む必要があります。

### 解決策

```yaml
if: ${{ secrets.SLACK_WEBHOOK_URL != '' }}
```

---

## 問題2: Invalid Project ARN フォーマット

### 問題

```
Invalid Project arn: arn:aws:devicefarm:us-west-2:***:project:meal-management-app-e2e-tests-dev
```

プロジェクト名から直接 ARN を構築しようとしてエラー。

### 原因

Device Farm の Project ARN は `project:6c101a5a-655b-4d75-875d-0a6d9c29f0e6` のような UUID 形式であり、プロジェクト名をそのまま ARN に含めることはできません。

### 解決策

`list-projects` API を使用してプロジェクト名から動的に ARN を取得：

```bash
PROJECT_ARN=$(aws devicefarm list-projects \
  --query "projects[?name=='$PROJECT_NAME'].arn" \
  --output text \
  --region us-west-2)
```

---

## 問題3: list-device-pools のパラメータ名

### 問題

```
the following arguments are required: --arn
```

`--project-arn` パラメータを使用してエラー。

### 原因

`list-device-pools` コマンドは `--project-arn` ではなく `--arn` を使用します。

### 解決策

```bash
# 誤り
aws devicefarm list-device-pools --project-arn "$PROJECT_ARN"

# 正しい
aws devicefarm list-device-pools --arn "$PROJECT_ARN"
```

---

## 問題4: schedule-run の --test パラメータ

### 問題

```
the following arguments are required: --test
```

`--test-type` と `--test-spec-arn` を別々のパラメータとして指定してエラー。

### 原因

`schedule-run` の `--test` パラメータは JSON 形式のオブジェクトを期待しています。

### 解決策

```bash
# 誤り
aws devicefarm schedule-run \
  --test-type "WEB" \
  --test-spec-arn "$TESTSPEC_ARN"

# 正しい（JSON オブジェクト）
aws devicefarm schedule-run \
  --test "{\"type\":\"APPIUM_WEB_NODE\",\"testPackageArn\":\"$TESTPACKAGE_ARN\",\"testSpecArn\":\"$TESTSPEC_ARN\"}"
```

---

## 問題5: 無効なテストタイプ "WEB"

### 問題

```
Value 'WEB' at 'test.type' failed to satisfy constraint:
Member must satisfy enum value set: [APPIUM_NODE, APPIUM_WEB_RUBY, APPIUM_WEB_PYTHON, ...]
```

### 原因

"WEB" は有効なテストタイプではありません。Device Farm では Appium ベースのテストタイプを使用します。

### 解決策

Node.js (Playwright) ベースの Web テストには `APPIUM_WEB_NODE` を使用：

```bash
--test "{\"type\":\"APPIUM_WEB_NODE\", ...}"
```

有効なテストタイプ一覧：
- `APPIUM_WEB_NODE` - Node.js ベースの Web テスト
- `APPIUM_WEB_PYTHON` - Python ベースの Web テスト
- `APPIUM_NODE` - Node.js ネイティブアプリテスト
- その他多数...

---

## 問題6: list-artifacts のパラメータ名

### 問題

```
the following arguments are required: --type
```

`--artifact-type` を使用してエラー。

### 原因

`list-artifacts` コマンドは `--artifact-type` ではなく `--type` を使用します。

### 解決策

```bash
# 誤り
aws devicefarm list-artifacts --arn "$TEST_RUN_ARN" --artifact-type "LOG"

# 正しい
aws devicefarm list-artifacts --arn "$TEST_RUN_ARN" --type "LOG"
```

---

## 問題7: get-upload のパラメータ

### 問題

```
Unknown options: --project-arn
```

### 原因

`get-upload` コマンドは `--arn` のみを受け付け、`--project-arn` は無効です。

### 解決策

```bash
# 誤り
aws devicefarm get-upload \
  --project-arn "$PROJECT_ARN" \
  --arn "$UPLOAD_ARN"

# 正しい
aws devicefarm get-upload --arn "$UPLOAD_ARN"
```

---

## 問題8: executionConfiguration の videoRecording

### 問題

```
Unknown parameter in executionConfiguration: "videoRecording",
must be one of: jobTimeoutMinutes, accountsCleanup, appPackagesCleanup, videoCapture, skipAppResign
```

### 原因

パラメータ名が `videoRecording` ではなく `videoCapture` です。

### 解決策

```bash
# 誤り
--execution-configuration '{"videoRecording":true}'

# 正しい
--execution-configuration '{"videoCapture":true}'
```

---

## 問題9: testSpecArn のみでは不十分

### 問題

```
Invalid input for ScheduleRun API detected. The service could not schedule a run
due to an invalid "testSpecArn" in your request.
```

### 原因

`APPIUM_WEB_NODE` テストでは、テストスペック（YAML）だけでなく、実際のテストコードを含むテストパッケージ（ZIP）も必要です。

### 解決策

1. テストパッケージ（ZIP）を作成・アップロード
2. テストスペック（YAML）をアップロード
3. 両方の ARN を `schedule-run` に渡す

```bash
# 1. テストパッケージの作成
zip -r test-package.zip e2e/ node_modules/ package.json playwright.config.ts

# 2. テストパッケージのアップロード
aws devicefarm create-upload \
  --type "APPIUM_WEB_NODE_TEST_PACKAGE" \
  --name "test-package.zip"

# 3. テストスペックのアップロード
aws devicefarm create-upload \
  --type "APPIUM_WEB_NODE_TEST_SPEC" \
  --name "testspec.yml"

# 4. 両方を指定してテスト実行
aws devicefarm schedule-run \
  --test "{\"type\":\"APPIUM_WEB_NODE\",\"testPackageArn\":\"$TESTPACKAGE_ARN\",\"testSpecArn\":\"$TESTSPEC_ARN\"}"
```

---

## 問題10: testspec.yml のバージョン番号

### 問題

```
"errorMessage":"The version number specified in the yaml file is incorrect."
"errorCode":"TEST_SPEC_VERSION_MISMATCH"
```

### 原因

Device Farm のテストスペックには `version: 0.1` を使用する必要があります。`version: 0.0` は無効です。

### 解決策

```yaml
# 誤り
version: 0.0

# 正しい
version: 0.1

phases:
  pre_test:
    commands:
      - npm ci
      - npx playwright install chromium
  test:
    commands:
      - npx playwright test
```

---

## 最終的な正しいワークフロー構成

### 1. テストパッケージのアップロード

```yaml
- name: Create test package ZIP
  run: |
    mkdir -p test-package
    cp -r e2e node_modules package.json playwright.config.ts test-package/
    cd test-package && zip -r ../test-package.zip .

- name: Upload test package
  run: |
    UPLOAD_RESPONSE=$(aws devicefarm create-upload \
      --project-arn "$PROJECT_ARN" \
      --type "APPIUM_WEB_NODE_TEST_PACKAGE" \
      --name "test-package.zip")

    UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.upload.url')
    curl -X PUT "$UPLOAD_URL" --data-binary "@test-package.zip"
```

### 2. テストスペックのアップロード

```yaml
- name: Upload testspec
  run: |
    UPLOAD_RESPONSE=$(aws devicefarm create-upload \
      --project-arn "$PROJECT_ARN" \
      --type "APPIUM_WEB_NODE_TEST_SPEC" \
      --name "testspec.yml")

    UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | jq -r '.upload.url')
    curl -X PUT "$UPLOAD_URL" --data-binary "@testspec.yml"
```

### 3. テスト実行のスケジュール

```yaml
- name: Schedule test run
  run: |
    aws devicefarm schedule-run \
      --project-arn "$PROJECT_ARN" \
      --device-pool-arn "$DEVICE_POOL_ARN" \
      --test "{\"type\":\"APPIUM_WEB_NODE\",\"testPackageArn\":\"$TESTPACKAGE_ARN\",\"testSpecArn\":\"$TESTSPEC_ARN\"}" \
      --execution-configuration '{"accountsCleanup":true,"appPackagesCleanup":true,"videoCapture":true}'
```

---

## 問題11: 全テストが実行されてしまう（コスト増大）

### 問題

testspec.yml で以下のように設定すると、**全ての E2E テスト**が Device Farm で実行されてしまう：

```yaml
test:
  commands:
    - npx playwright test --project=chromium
```

8個のテストファイル × 複数デバイス = 65 ジョブが生成され、実行時間・コストが大幅に増大。

### 原因

`npx playwright test` はデフォルトで `e2e/` フォルダ内の全てのテストファイルを実行します。

### 解決策

Device Farm ではクリティカルパステストのみを実行するよう、特定のテストファイルを指定：

```yaml
# 誤り - 全テスト実行（8ファイル × 複数デバイス = 65ジョブ）
- npx playwright test --project=chromium

# 正しい - クリティカルパスのみ（1ファイル × 複数デバイス = 少数ジョブ）
- npx playwright test e2e/critical-path.spec.ts --project=chromium
```

### ベストプラクティス

| 環境 | 実行するテスト | 理由 |
|-----|-------------|-----|
| Device Farm | critical-path.spec.ts のみ | コスト最適化、実デバイス検証 |
| GitHub Actions | 全テスト | 無料枠活用、高速実行 |

---

## 問題12: Android テストが SKIPPED になる（totalJobs: 0）

### 問題

Device Farm でテスト実行をスケジュールすると、Android テストが `SKIPPED` ステータスで、`totalJobs: 0` となる：

```json
{
  "name": "Android Test Run",
  "result": "SKIPPED",
  "counters": {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0
  }
}
```

### 原因

デバイスプールのルールで `MANUFACTURER="Samsung"` を使用していたが、`APPIUM_WEB_NODE` テストタイプとの互換性に問題があった。

### 解決策

`MANUFACTURER` 属性の代わりに `PLATFORM` 属性を使用：

```hcl
# 誤り - APPIUM_WEB_NODE との互換性問題
rule {
  attribute = "MANUFACTURER"
  operator  = "EQUALS"
  value     = "\"Samsung\""
}

# 正しい - PLATFORM 属性でより広いデバイス互換性
rule {
  attribute = "PLATFORM"
  operator  = "EQUALS"
  value     = "\"ANDROID\""
}
```

---

## 問題13: デバイスプールのデバイス数が多すぎる（コスト爆発）

### 問題

1回のテスト実行で 65 ジョブが生成され、コストが爆発的に増大：

```
Test Run Status: RUNNING
totalJobs: 65
```

### 原因

`max_devices` が設定されていない（デフォルト 0 = 無制限）ため、プール内の全デバイスでテストが並列実行された。

### 解決策

`max_devices = 1` を設定して、1回のテスト実行で使用するデバイス数を制限：

```hcl
resource "aws_devicefarm_device_pool" "android" {
  name        = "my-android-pool"
  project_arn = aws_devicefarm_project.main.arn
  max_devices = 1  # 重要: コスト最適化

  rule {
    attribute = "PLATFORM"
    operator  = "EQUALS"
    value     = "\"ANDROID\""
  }
}
```

### コスト最適化のベストプラクティス

| 設定 | 推奨値 | 理由 |
|-----|-------|-----|
| max_devices | 1 | 1デバイスで十分な検証が可能 |
| テスト数 | 5個（スモークテスト） | 10分以内完了目標 |
| タイムアウト | 60秒/テスト | 異常なハングを防止 |

---

## 問題14: Android デバイスが全て SKIPPED になる（Amazon Linux 2 必須）

### 問題

APPIUM_WEB_NODE テストで Android デバイスを使用しようとすると、全デバイスが SKIPPED になる：

```json
{
  "result": "SKIPPED",
  "message": "{\"skippedDevices\":[{\"Samsung Galaxy A25\":[\"Android devices require a test spec file which has selected the Amazon Linux 2 test host\"]}...}"
}
```

### 原因

APPIUM_WEB_NODE テストタイプで Android デバイスを使用するには、testspec.yml で Amazon Linux 2 テストホストを**トップレベル**で明示的に指定する必要があります。

**注意**: `configuration.testHostType` は Device Farm では認識されません。

### 解決策

testspec.yml の**トップレベル**に `android_test_host` と `ios_test_host` を追加：

```yaml
version: 0.1

# テストホスト指定（トップレベルに配置 - 必須）
android_test_host: amazon_linux_2
ios_test_host: macos_sequoia  # 注: mac_os_sonoma は無効

phases:
  pre_test:
    commands:
      - npm ci
      - npx playwright install chromium
  test:
    commands:
      - npx playwright test e2e/smoke-test.spec.ts --project=chromium
```

参考: [AWS Device Farm - Amazon Linux 2 Test Spec Example](https://docs.aws.amazon.com/devicefarm/latest/developerguide/amazon-linux-2-test-spec-file-example.html)

---

## 問題15: iOS デバイスが全て SKIPPED になる（無効なテストホスト名）

### 問題

iOS テストでデバイスが SKIPPED になり、以下のエラーメッセージが表示される：

```json
{
  "result": "SKIPPED",
  "message": "{\"skippedDevices\":[{\"Apple iPhone 13\":[\"The selected test host 'mac_os_sonoma' is not valid\"]}...]}"
}
```

### 原因

`ios_test_host` に無効な値 `mac_os_sonoma` を指定していた。Device Farm で有効な iOS テストホスト名は `macos_sequoia` です。

### 解決策

testspec.yml の `ios_test_host` を正しい値に修正：

```yaml
# 誤り - 無効なテストホスト名
ios_test_host: mac_os_sonoma

# 正しい - 有効なテストホスト名
ios_test_host: macos_sequoia
```

参考: [AWS Device Farm - Test environment for iOS devices](https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environments-hosts-ios.html)

---

## まとめ

AWS Device Farm の API は、パラメータ名や値に細かい違いがあり、ドキュメントだけでは把握しにくい部分があります。主な注意点：

1. **ARN は動的に取得** - プロジェクト名から構築せず `list-projects` で取得
2. **パラメータ名の確認** - `--project-arn` vs `--arn`、`--type` vs `--artifact-type` など
3. **JSON 形式のパラメータ** - `--test` は JSON オブジェクトで指定
4. **テストタイプの選択** - "WEB" ではなく `APPIUM_WEB_NODE` など Appium ベースを使用
5. **必要なアップロード** - テストパッケージとテストスペックの両方が必要
6. **バージョン番号** - testspec.yml は `version: 0.1` を使用
7. **テスト範囲** - クリティカルパスのみに限定してコスト最適化
8. **デバイス数制限** - `max_devices = 1` でコスト最適化
9. **PLATFORM 属性** - MANUFACTURER より PLATFORM を使用して互換性向上
10. **Amazon Linux 2** - Android デバイスには `android_test_host: amazon_linux_2` が必須
11. **macOS Sequoia** - iOS デバイスには `ios_test_host: macos_sequoia` を使用（`mac_os_sonoma` は無効）

これらの落とし穴を避けることで、Device Farm を使用した CI/CD パイプラインを正しく構築できます。

---

## 参考リンク

- [AWS Device Farm API Reference](https://docs.aws.amazon.com/devicefarm/latest/APIReference/Welcome.html)
- [Custom Test Environments](https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environments.html)
- [Test Spec YAML Syntax](https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environment-yaml-syntax.html)
