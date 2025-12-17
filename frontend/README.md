# 食事管理アプリ - フロントエンド

React + TypeScript + Vite で構築された食事管理アプリケーションのフロントエンドです。

## 技術スタック

- **フレームワーク**: React 19
- **言語**: TypeScript
- **ビルドツール**: Vite
- **ルーティング**: React Router v7
- **認証**: Amazon Cognito + LINE LIFF
- **HTTPクライアント**: Axios
- **E2Eテスト**: Playwright

## セットアップ

### 依存関係のインストール

```bash
npm install
```

### 環境変数の設定

`.env.example` をコピーして `.env` ファイルを作成し、必要な環境変数を設定してください。

```bash
cp .env.example .env
```

必要な環境変数:
- `VITE_API_BASE_URL`: API Gateway URL
- `VITE_COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `VITE_COGNITO_CLIENT_ID`: Cognito Client ID
- `VITE_LIFF_ID`: LINE LIFF アプリケーション ID（LIFF 認証使用時）

## 開発

### 開発サーバーの起動

```bash
npm run dev
```

ブラウザで http://localhost:5173 を開きます。

### ビルド

```bash
npm run build
```

### プレビュー

```bash
npm run preview
```

## テスト

### E2Eテストの実行

```bash
# ヘッドレスモードで実行
npm run test:e2e

# UIモードで実行
npm run test:e2e:ui

# ヘッド付きモードで実行（ブラウザが表示される）
npm run test:e2e:headed
```

## プロジェクト構造

```
frontend/
├── e2e/              # E2Eテスト (Playwright)
├── src/
│   ├── api/          # APIクライアント
│   ├── components/   # 再利用可能なコンポーネント
│   ├── contexts/     # Reactコンテキスト
│   │   ├── AuthContext.tsx        # Cognito認証コンテキスト
│   │   ├── LiffContext.tsx        # LINE LIFF認証コンテキスト
│   │   └── UnifiedAuthContext.tsx # 統合認証コンテキスト
│   ├── hooks/        # カスタムフック
│   ├── pages/        # ページコンポーネント
│   ├── types/        # TypeScript型定義
│   ├── utils/        # ユーティリティ関数
│   ├── App.tsx       # メインアプリケーションコンポーネント
│   └── main.tsx      # エントリーポイント
├── playwright.config.ts  # Playwright設定
└── vite.config.ts        # Vite設定
```

## 認証アーキテクチャ

本アプリケーションは **LINE ユーザー** と **ブラウザユーザー** の両方に対応しています。

### 認証フロー

| 環境 | 認証方式 | コンテキスト |
|------|----------|--------------|
| LINE アプリ内 (LIFF) | LINE ID Token → Cognito Custom Auth | `LiffContext` |
| ブラウザ | Email/Password → Cognito Standard Auth | `AuthContext` |

### 統合認証

`UnifiedAuthContext` が実行環境を自動検出し、適切な認証フローを選択します：

1. **LIFF 環境検出**: `liff.isInClient()` で LINE アプリ内かを判定
2. **認証開始**: 環境に応じて LIFF 認証または Cognito 認証を開始
3. **トークン取得**: どちらの経路でも最終的に Cognito JWT Token を取得
4. **API アクセス**: 統一された JWT Token で API Gateway にアクセス

---

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
