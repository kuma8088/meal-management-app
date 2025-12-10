import React, { useEffect, useState } from 'react'
import { GetServerSideProps } from 'next'
import { getSession, signOut } from 'next-auth/react'
import Link from 'next/link'
import { Card, Alert, Loading } from '@/components'
import { api } from '@/lib/api-client'
import { requireAuth } from '@/lib/auth-middleware'

interface DailySummary {
  date: string
  totalCalories: number
  totalProtein: number
  totalFat: number
  totalCarbs: number
  mealCount: number
  tdee: number
}

export default function Home() {
  const [summary, setSummary] = useState<DailySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await api.getDailySummary()
        setSummary(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '日次サマリーの読み込みに失敗しました')
      } finally {
        setLoading(false)
      }
    }

    fetchSummary()
  }, [])

  if (loading) {
    return <Loading message="データを読み込み中..." fullScreen={false} />
  }

  const calorieProgress = summary
    ? Math.min((summary.totalCalories / summary.tdee) * 100, 100)
    : 0

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ヘッダー */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">食事管理アプリ</h1>
          <button
            onClick={() => signOut({ redirect: true, callbackUrl: '/login' })}
            className="text-gray-600 hover:text-gray-900 font-medium"
          >
            ログアウト
          </button>
        </div>
      </header>

      {/* メインコンテンツ */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <Alert
            type="error"
            title="エラー"
            message={error}
            onClose={() => setError(null)}
          />
        )}

        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* カロリー情報 */}
            <Card
              header={
                <h2 className="text-lg font-semibold text-gray-900">
                  本日のカロリー
                </h2>
              }
            >
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="text-gray-600">摂取カロリー</span>
                    <span className="font-bold text-indigo-600">
                      {summary.totalCalories} kcal
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-indigo-600 h-3 rounded-full transition-all"
                      style={{ width: `${calorieProgress}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-sm text-gray-500 mt-1">
                    <span>目標: {summary.tdee} kcal</span>
                    <span>{Math.round(calorieProgress)}%</span>
                  </div>
                </div>
              </div>
            </Card>

            {/* 栄養素情報 */}
            <Card
              header={
                <h2 className="text-lg font-semibold text-gray-900">
                  栄養素
                </h2>
              }
            >
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600">タンパク質</span>
                  <span className="font-semibold">{summary.totalProtein}g</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">脂質</span>
                  <span className="font-semibold">{summary.totalFat}g</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">炭水化物</span>
                  <span className="font-semibold">{summary.totalCarbs}g</span>
                </div>
              </div>
            </Card>

            {/* 食事記録 */}
            <Card
              header={
                <h2 className="text-lg font-semibold text-gray-900">
                  本日の食事
                </h2>
              }
            >
              <div>
                <p className="text-3xl font-bold text-indigo-600 mb-2">
                  {summary.mealCount}
                </p>
                <p className="text-gray-600">食事記録</p>
              </div>
            </Card>

            {/* クイックアクション */}
            <Card
              header={
                <h2 className="text-lg font-semibold text-gray-900">
                  クイックアクション
                </h2>
              }
            >
              <div className="space-y-2">
                <Link
                  href="/meals/new"
                  className="block w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-lg text-center transition"
                >
                  食事を記録
                </Link>
                <Link
                  href="/meals"
                  className="block w-full bg-gray-200 hover:bg-gray-300 text-gray-900 font-semibold py-2 px-4 rounded-lg text-center transition"
                >
                  食事履歴
                </Link>
              </div>
            </Card>
          </div>
        )}

        {/* ナビゲーション */}
        <Card>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Link
              href="/profile"
              className="p-4 bg-blue-50 hover:bg-blue-100 rounded-lg text-center transition"
            >
              <p className="text-2xl mb-2">👤</p>
              <p className="font-semibold text-gray-900">プロフィール</p>
            </Link>
            <Link
              href="/goals"
              className="p-4 bg-green-50 hover:bg-green-100 rounded-lg text-center transition"
            >
              <p className="text-2xl mb-2">🎯</p>
              <p className="font-semibold text-gray-900">目標</p>
            </Link>
            <Link
              href="/meals"
              className="p-4 bg-yellow-50 hover:bg-yellow-100 rounded-lg text-center transition"
            >
              <p className="text-2xl mb-2">🍽️</p>
              <p className="font-semibold text-gray-900">食事記録</p>
            </Link>
            <Link
              href="/summary"
              className="p-4 bg-purple-50 hover:bg-purple-100 rounded-lg text-center transition"
            >
              <p className="text-2xl mb-2">📊</p>
              <p className="font-semibold text-gray-900">サマリー</p>
            </Link>
          </div>
        </Card>
      </main>
    </div>
  )
}

export const getServerSideProps: GetServerSideProps = requireAuth(
  async (context) => {
    return { props: {} }
  }
)
