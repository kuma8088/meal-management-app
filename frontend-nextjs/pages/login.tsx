import React from 'react'
import { signIn } from 'next-auth/react'
import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'

export default function Login() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const { error } = router.query

  const handleSignIn = async () => {
    setIsLoading(true)
    await signIn('cognito', { redirect: true, callbackUrl: '/' })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 text-center">
          食事管理アプリ
        </h1>
        <p className="text-gray-600 text-center mb-8">
          あなたの健康をサポートします
        </p>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm font-medium">
              ログインに失敗しました。もう一度お試しください。
            </p>
          </div>
        )}

        <button
          onClick={handleSignIn}
          disabled={isLoading}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white font-semibold py-3 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <span className="inline-block animate-spin">⏳</span>
              ログイン中...
            </>
          ) : (
            'Cognito でログイン'
          )}
        </button>

        <p className="text-gray-600 text-xs text-center mt-6">
          ログインすることで、プライバシーポリシーに同意します。
        </p>
      </div>
    </div>
  )
}
