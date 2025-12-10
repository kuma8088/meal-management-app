import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
  return (
    <Html lang="ja">
      <Head>
        {/* SEO Meta Tags */}
        <meta charSet="utf-8" />
        <meta name="description" content="AI を活用した食事管理アプリ。栄養情報の自動計算、体重目標管理、パーソナライズされたアドバイスを提供します。" />
        <meta name="keywords" content="食事管理, 栄養計算, 目標管理, AI アドバイス, 健康管理" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#4f46e5" />

        {/* Open Graph Tags */}
        <meta property="og:title" content="食事管理アプリ - AI で楽しく健康管理" />
        <meta property="og:description" content="AI を活用した食事管理アプリ。栄養情報の自動計算、体重目標管理、パーソナライズされたアドバイスを提供します。" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://meal-management-app.example.com" />
        <meta property="og:image" content="https://meal-management-app.example.com/og-image.png" />

        {/* Twitter Card Tags */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="食事管理アプリ - AI で楽しく健康管理" />
        <meta name="twitter:description" content="AI を活用した食事管理アプリ。栄養情報の自動計算、体重目標管理、パーソナライズされたアドバイスを提供します。" />
        <meta name="twitter:image" content="https://meal-management-app.example.com/og-image.png" />

        {/* Icons */}
        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />

        {/* Preconnect to external domains */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  )
}
