# E2Eテスト ネットワークエラー解決記録

## 概要

Playwright E2Eテストで93件のテストが「ネットワークエラーが発生しました」で失敗していた問題を解決した記録。

**解決日**: 2025-12-06
**解決者**: Claude Opus 4.5
**問題の深刻度**: 高（全テストの約30%が失敗）

---

## Claude Sonnet vs Opus: アプローチの違い

### Claude Sonnet 4.5 のアプローチ（解決失敗）

Sonnetは以下の修正を試みたが、根本原因に到達できなかった：

| 試みた修正 | 内容 | 結果 |
|-----------|------|------|
| AuthContext修正 | localStorageからの認証情報復元を追加 | ❌ 問題解決せず |
| ページコンポーネント修正 | authLoading状態を待つように修正 | ❌ 問題解決せず |
| API Gateway確認 | curlで直接アクセスして動作確認 | ✅ 正常動作を確認 |
| CORS設定確認 | プリフライトリクエストの確認 | ✅ 正常設定を確認 |

**Sonnetの限界**:
- 「curlで成功する」→「API Gatewayは正常」と結論
- ブラウザ環境との違いを深掘りしなかった
- **エラーの表面的な症状（認証、CORS）に焦点を当て続けた**
- Viteの環境変数読み込みメカニズムまで調査が及ばなかった

### Claude Opus 4.5 のアプローチ（解決成功）

Opusは以下の体系的なデバッグを行った：

| ステップ | 内容 | 発見 |
|---------|------|------|
| 1. デバッグログ追加 | Playwrightのnetworkイベントをログ出力 | リクエストがAPI Gatewayに到達していない |
| 2. エラー詳細確認 | `net::ERR_CONNECTION_REFUSED` の意味を分析 | 接続先が存在しない（CORSではない） |
| 3. 環境変数調査 | `.env` と `.env.test` の内容を比較 | 異なるAPI URLが設定されていた |
| 4. Vite設定調査 | playwright.config.tsのwebServer設定を確認 | `npm run dev` が `.env` を読み込んでいた |
| 5. 根本原因特定 | Viteの `--mode` フラグの動作を理解 | `.env.test` が読み込まれていなかった |

**Opusの成功要因**:
1. **「リクエストが送信されていない」という事実の発見**
   - デバッグログで `>> Request:` が出力されないことを確認
   - これにより「API Gateway側の問題ではない」と判断できた

2. **サブプロセスの環境変数という観点**
   - Playwright → Vite（子プロセス）の関係を理解
   - 子プロセスが親とは異なる環境変数を持つ可能性を検討

3. **Viteのmode機能の知識**
   - `--mode` フラグで `.env.[mode]` を読み込めることを把握
   - 1行の修正で問題を解決

### 比較まとめ

```
Sonnet: 症状 → 仮説（CORS/認証） → 修正 → 失敗 → 同じ仮説で再試行（ループ）

Opus:   症状 → デバッグログ追加 → 事実確認 → 仮説修正 → 根本原因特定 → 解決
```

**決定的な違い**:
- Sonnetは「何が起きているか」の確認なしに修正を試みた
- Opusは「リクエストがどこに送られているか」を実際に確認した

---

## 問題の症状

### エラーメッセージ
```
Console error: No response received: XMLHttpRequest
Console error: Failed to load resource: net::ERR_CONNECTION_REFUSED
```

### 影響範囲
- 93件のE2Eテストが失敗
- 全ての認証が必要なページ（Goals, Summary, Profile, Meals, Foods）で発生
- スクリーンショットには「ネットワークエラーが発生しました」と表示

---

## 調査プロセス

### 1. 最初の仮説（誤り）
- CORSの設定問題 → curlで確認したところ正常
- Cognito認証の問題 → トークンは正常に発行されていた
- API Gatewayの設定問題 → 直接curlでアクセスすると正常応答

### 2. 重要な発見
curlでAPI Gatewayに直接アクセスすると成功するが、Playwrightブラウザからは失敗する。

```bash
# これは成功
curl -s "https://868t2tljy9.execute-api.ap-northeast-1.amazonaws.com/dev/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN"
# → HTTP 200 OK

# これは失敗（Playwrightブラウザ内）
# → net::ERR_CONNECTION_REFUSED
```

### 3. デバッグログの追加
goals.spec.tsにネットワークリクエストのログを追加：

```typescript
page.on('request', request => {
  if (request.url().includes('execute-api')) {
    console.log(`>> Request: ${request.method()} ${request.url()}`);
  }
});
```

**結果**: `>> Request:` のログが出力されなかった

→ リクエストがAPI Gatewayに到達していない

### 4. 環境変数の確認

`.env` ファイル（Viteがデフォルトで読み込む）:
```
VITE_API_BASE_URL=http://localhost:3000
```

`.env.test` ファイル（テスト用）:
```
VITE_API_BASE_URL=https://868t2tljy9.execute-api.ap-northeast-1.amazonaws.com/dev
```

---

## 根本原因

### playwright.config.ts の webServer 設定

```typescript
webServer: {
  command: 'npm run dev',  // ← 問題の箇所
  url: 'http://localhost:5173',
  reuseExistingServer: !process.env.CI,
  timeout: 120 * 1000,
},
```

`npm run dev` は `vite` を実行するが、**Viteはデフォルトで `.env` を読み込む**。

### 処理フロー

1. `playwright test` 実行
2. Playwrightが `npm run dev` でViteを起動
3. Viteが `.env` を読み込む（`.env.test` ではない）
4. `VITE_API_BASE_URL=http://localhost:3000` が設定される
5. フロントエンドが `localhost:3000` にAPIリクエストを送信
6. `localhost:3000` には何も起動していない
7. `net::ERR_CONNECTION_REFUSED` が発生

---

## 解決策

### playwright.config.ts の修正

```typescript
webServer: {
  command: 'vite --mode test',  // ← 修正後
  url: 'http://localhost:5173',
  reuseExistingServer: !process.env.CI,
  timeout: 120 * 1000,
},
```

### Viteの --mode フラグ

`vite --mode test` を使用すると、Viteは以下の順序で環境変数を読み込む：

1. `.env` （ベース）
2. `.env.test` （modeに応じてオーバーライド）

これにより、`.env.test` の `VITE_API_BASE_URL` が正しく適用される。

---

## 結果

| 項目 | 修正前 | 修正後 |
|------|--------|--------|
| 失敗テスト数 | 93 | 10 |
| 成功テスト数 | 不明 | 79 |
| 成功率 | 約70% | 約88% |

残り10件の失敗はネットワークエラーではなく、テストの期待値とUIの不一致。

---

## 教訓

### 1. 環境変数の読み込み順序を理解する

Viteの環境変数読み込み順序:
- `.env` - 常に読み込まれる
- `.env.local` - 常に読み込まれる（gitignore推奨）
- `.env.[mode]` - 指定されたモードでのみ読み込まれる
- `.env.[mode].local` - 指定されたモードでのみ読み込まれる

### 2. サブプロセスの環境変数に注意

Playwrightの `webServer.command` で起動されるプロセスは、親プロセス（playwright test）とは別の環境変数を持つ可能性がある。

### 3. curlとブラウザの違い

curlで成功してもブラウザで失敗する場合、以下を疑う：
- CORS（ただし今回は該当せず）
- 環境変数の設定
- プロキシ設定
- ビルド時の設定（import.meta.env は**ビルド時**に解決される）

### 4. デバッグログの重要性

ネットワークリクエストのログを追加することで、リクエストがそもそも送信されていないことを発見できた。

---

## 関連ファイル

- `frontend/playwright.config.ts` - webServer設定
- `frontend/.env` - ローカル開発用環境変数
- `frontend/.env.test` - E2Eテスト用環境変数
- `frontend/src/api/client.ts` - APIクライアント（VITE_API_BASE_URLを使用）

---

## 参考リンク

- [Vite 環境変数とモード](https://ja.vitejs.dev/guide/env-and-mode.html)
- [Playwright webServer設定](https://playwright.dev/docs/test-webserver)
