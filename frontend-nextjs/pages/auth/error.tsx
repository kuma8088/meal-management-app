import React from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'

export default function AuthError() {
  const router = useRouter()
  const { error } = router.query

  const errorMessages: { [key: string]: string } = {
    'OAuthCallback': 'Cognito認証に失敗しました。もう一度お試しください。',
    'OAuthCreateAccount': 'アカウント作成に失敗しました。',
    'OAuthSignin': 'ログインに失敗しました。',
    'CredentialsSignin': '認証情報が無効です。',
    'Default': '予期しないエラーが発生しました。',
  }

  const message = errorMessages[error as string] || errorMessages['Default']

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md text-center">
        <div className="mb-6">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-900">認証エラー</h1>
        </div>

        <p className="text-gray-700 mb-8">
          {message}
        </p>

        <div className="flex gap-4">
          <Link
            href="/login"
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
          >
            ログインに戻る
          </Link>
          <button
            onClick={() => router.push('/')}
            className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-900 font-semibold py-2 px-4 rounded-lg transition duration-200"
          >
            ホームに戻る
          </button>
        </div>

        {process.env.NODE_ENV === 'development' && (
          <p className="text-xs text-gray-500 mt-6 p-3 bg-gray-100 rounded">
            Error Code: {error || 'Unknown'}
          </p>
        )}
      </div>
    </div>
  )
}
