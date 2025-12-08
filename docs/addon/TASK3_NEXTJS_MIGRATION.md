# タスク3: Next.js フロントエンド移行

## 概要

React + Vite から Next.js Pages Router への段階的移行。既存 Playwright テストを再利用し、段階的に Pages Router → App Router（将来）へ移行。

## 新規要件

| 要件ID | 説明 |
|--------|------|
| 要件3.1 | Next.js Pages Router の初期化 |
| 要件3.2 | NextAuth.js + Cognito 認証統合 |
| 要件3.3 | 既存 React コンポーネントの段階的移植 |
| 要件3.4 | SEO・メタデータの最適化 |
| 要件3.5 | AWS Amplify Hosting でのデプロイ |
| 要件3.6 | 既存 Playwright E2E テストの互換性確保 |

## 新規設計

### 段階的移行アーキテクチャ

```
フェーズ A: 認証層の整備
  ├─ Next.js Pages Router 初期化
  ├─ NextAuth.js 設定
  └─ Cognito プロバイダー統合

フェーズ B: SEO 重点ページ移行
  ├─ ホーム
  ├─ プロフィール
  └─ 目標設定

フェーズ C: 残りのページ移行
  ├─ 食事登録
  ├─ 食事一覧
  └─ 総評

フェーズ D: インフラ統合
  └─ AWS Amplify Hosting デプロイ

（App Router 移行は後続フェーズ、オプション）
```

### ディレクトリ構造（Pages Router）

```
frontend-nextjs/
├── pages/
│   ├── _app.tsx                   # App ルート
│   ├── _document.tsx              # HTML ドキュメント
│   ├── index.tsx                  # リダイレクト
│   ├── login.tsx                  # ログイン
│   ├── profile.tsx                # プロフィール
│   ├── goals.tsx                  # 目標設定
│   ├── foods.tsx                  # 食品検索
│   ├── meals/
│   │   ├── index.tsx              # 食事一覧
│   │   └── new.tsx                # 食事登録
│   └── summary.tsx                # 総評
├── components/                    # 既存から移植
├── lib/
│   ├── auth.ts                    # NextAuth 設定
│   └── api-client.ts              # API クライアント
├── middleware.ts                  # 認証ミドルウェア
├── next.config.js
├── tailwind.config.ts
└── package.json
```

### NextAuth.js 設定

```typescript
// lib/auth.ts
export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    CognitoProvider({
      clientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID,
      clientSecret: process.env.COGNITO_CLIENT_SECRET,
      issuer: process.env.COGNITO_ISSUER,
    })
  ],
  session: { strategy: "jwt" },
  pages: { signIn: '/login' },
})

// middleware.ts
export { auth as middleware } from "@/lib/auth"
export const config = {
  matcher: ['/((?!api|_next|login).*)'],
}
```

### 新規リソース

#### 新規プロジェクト
- **ディレクトリ**: `frontend-nextjs/`
- **フレームワーク**: Next.js 14 (Pages Router)
- **認証**: NextAuth.js v5
- **スタイル**: Tailwind CSS（既存から継続）
- **デプロイ**: AWS Amplify Hosting

#### 環境変数（Amplify 設定）

```
NEXT_PUBLIC_API_BASE_URL={API_GATEWAY_URL}
NEXT_PUBLIC_COGNITO_USER_POOL_ID={USER_POOL_ID}
NEXT_PUBLIC_COGNITO_CLIENT_ID={CLIENT_ID}
COGNITO_CLIENT_SECRET={SECRET}
COGNITO_ISSUER={ISSUER_URL}
```

#### Amplify Hosting ビルド設定

```
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend-nextjs
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: frontend-nextjs/.next
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

### ページ移行順序（ビジネス価値優先）

| フェーズ | ページ | 工数 | 理由 |
|---------|--------|------|------|
| Phase 1 | ログイン（認証層） | 4-6h | すべてのページの基盤 |
| Phase 2a | ホーム | 2-3h | SEO・ランディング重要 |
| Phase 2b | プロフィール | 3-4h | 初期設定の必須ページ |
| Phase 2c | 目標設定 | 3-4h | コアワークフロー |
| Phase 3a | 食事登録 | 3-4h | メインの使用フロー |
| Phase 3b | 食事一覧 | 2-3h | 記録確認 |
| Phase 3c | 総評 | 2-3h | AI アドバイス表示 |

## 工数見積もり（最適化版）

| フェーズ | 工数 | 詳細 |
|---------|------|------|
| Phase 1: プロジェクト初期化 | 2-3h | 依存関係インストール、基本設定 |
| Phase 2: 認証層 | 4-6h | NextAuth + Cognito、ミドルウェア |
| Phase 3: コンポーネント移植 | 6-8h | 既存から移植、props 互換性確保 |
| Phase 4: ページ移行 | 8-10h | 7ページの段階的実装 |
| Phase 5: API クライアント | 2-3h | 既存 axios クライアント再利用 |
| Phase 6: Amplify 設定 | 2-3h | ホスティング・ビルド設定 |
| Phase 7: テスト検証 | 2-3h | Playwright テスト互換性確保 |
| **合計** | **25-35h** | 計画から45%削減 |

## 完了基準

- [ ] Next.js Pages Router でアプリケーションが動作する
- [ ] NextAuth.js で Cognito 認証が機能する
- [ ] 全 7 ページが実装される
- [ ] Amplify Hosting で本番デプロイが可能
- [ ] 既存 Playwright テストが Next.js URL で成功する
- [ ] SEO・メタデータが設定される

## リスク管理

| リスク | 影響 | 対策 |
|--------|------|------|
| 認証システム移行の複雑性 | 高 | Pages Router で安定化してから App Router へ |
| Tailwind 変換の工数増加 | 中 | 段階的変換、既存 CSS も並行利用 |
| Playwright テストの全面書き換え | 高 | Next.js 移行完了後に Device Farm 再調整 |

## 将来拡張（オプション）

### Phase 4: App Router 移行
- Pages Router が安定してから、6ヶ月後に検討
- Server Components、Streaming の活用
- **工数**: 20-30 時間（別途計画）

### 追加最適化
- Image Optimization
- Dynamic Imports
- Incremental Static Regeneration (ISR)

---

**次**: ユーザーテスト・本番デプロイに進む
