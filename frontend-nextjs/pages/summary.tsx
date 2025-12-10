import React, { useEffect, useState } from 'react'
import { GetServerSideProps } from 'next'
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
  advice: string
}

export default function Summary() {
  const [summary, setSummary] = useState<DailySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const data = await api.getDailySummary()
        const advice = await api.getAdvice()
        setSummary({ ...data, advice })
      } catch (err) {
        setError(err instanceof Error ? err.message : 'サマリーの読み込みに失敗しました')
      } finally {
        setLoading(false)
      }
    }

    fetchSummary()
  }, [])

  if (loading) {
    return <Loading message="サマリーを読み込み中..." fullScreen />
  }

  if (!summary) {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-2xl mx-auto">
          <Alert type="error" message="サマリーが見つかりません" />
        </div>
      </div>
    )
  }

  const caloriePercentage = (summary.totalCalories / summary.tdee) * 100
  const macroTotal = summary.totalProtein + summary.totalFat + summary.totalCarbs

  const proteinPercentage = (summary.totalProtein / macroTotal) * 100 || 0
  const fatPercentage = (summary.totalFat / macroTotal) * 100 || 0
  const carbsPercentage = (summary.totalCarbs / macroTotal) * 100 || 0

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        {/* ヘッダー */}
        <div className="mb-6 flex items-center gap-4">
          <Link href="/home" className="text-indigo-600 hover:text-indigo-700 font-semibold">
            ← ホームに戻る
          </Link>
        </div>

        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError(null)}
          />
        )}

        {/* 日付表示 */}
        <h1 className="text-3xl font-bold text-gray-900 mb-6">
          {new Date(summary.date).toLocaleDateString('ja-JP', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'long',
          })}
        </h1>

        {/* メインサマリー */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* カロリーサマリー */}
          <Card header={<h2 className="text-lg font-bold">カロリー摂取</h2>}>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-gray-600">摂取</span>
                  <span className="font-bold text-indigo-600">
                    {Math.round(summary.totalCalories)} kcal
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-indigo-600 h-3 rounded-full transition-all"
                    style={{ width: `${Math.min(caloriePercentage, 100)}%` }}
                  />
                </div>
              </div>
              <div className="flex justify-between text-sm text-gray-600">
                <span>目標: {summary.tdee} kcal</span>
                <span>{Math.round(caloriePercentage)}%</span>
              </div>
              <div className="pt-3 border-t border-gray-200">
                <p className="text-sm text-gray-600 mb-2">
                  {caloriePercentage < 80
                    ? '目標に向けてもう少し摂取が必要です'
                    : caloriePercentage <= 110
                    ? '目標範囲内です'
                    : '目標を少し超えています'}
                </p>
              </div>
            </div>
          </Card>

          {/* 食事記録数 */}
          <Card header={<h2 className="text-lg font-bold">食事記録</h2>}>
            <div className="space-y-4">
              <div className="text-center">
                <p className="text-4xl font-bold text-indigo-600 mb-2">
                  {summary.mealCount}
                </p>
                <p className="text-gray-600">食事記録</p>
              </div>
              <div className="pt-3 border-t border-gray-200">
                <Link
                  href="/meals/new"
                  className="block w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-lg text-center transition"
                >
                  + 食事を追加
                </Link>
              </div>
            </div>
          </Card>
        </div>

        {/* PFCバランス */}
        <Card className="mb-6" header={<h2 className="text-lg font-bold">栄養素バランス</h2>}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="text-center">
              <div className="relative w-24 h-24 mx-auto mb-4">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-xs text-gray-600">P</p>
                    <p className="text-lg font-bold text-red-600">
                      {Math.round(proteinPercentage)}%
                    </p>
                  </div>
                </div>
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="8"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    fill="none"
                    stroke="#dc2626"
                    strokeWidth="8"
                    strokeDasharray={`${(proteinPercentage / 100) * 251.2} 251.2`}
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <p className="text-sm font-semibold text-gray-900 mb-1">タンパク質</p>
              <p className="text-lg font-bold text-red-600">
                {Math.round(summary.totalProtein)}g
              </p>
            </div>

            <div className="text-center">
              <div className="relative w-24 h-24 mx-auto mb-4">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-xs text-gray-600">F</p>
                    <p className="text-lg font-bold text-yellow-600">
                      {Math.round(fatPercentage)}%
                    </p>
                  </div>
                </div>
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="8"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    fill="none"
                    stroke="#eab308"
                    strokeWidth="8"
                    strokeDasharray={`${(fatPercentage / 100) * 251.2} 251.2`}
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <p className="text-sm font-semibold text-gray-900 mb-1">脂質</p>
              <p className="text-lg font-bold text-yellow-600">
                {Math.round(summary.totalFat)}g
              </p>
            </div>

            <div className="text-center">
              <div className="relative w-24 h-24 mx-auto mb-4">
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-xs text-gray-600">C</p>
                    <p className="text-lg font-bold text-green-600">
                      {Math.round(carbsPercentage)}%
                    </p>
                  </div>
                </div>
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="8"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="40"
                    fill="none"
                    stroke="#16a34a"
                    strokeWidth="8"
                    strokeDasharray={`${(carbsPercentage / 100) * 251.2} 251.2`}
                    strokeLinecap="round"
                  />
                </svg>
              </div>
              <p className="text-sm font-semibold text-gray-900 mb-1">炭水化物</p>
              <p className="text-lg font-bold text-green-600">
                {Math.round(summary.totalCarbs)}g
              </p>
            </div>
          </div>
        </Card>

        {/* AIアドバイス */}
        <Card
          className="mb-6"
          header={
            <h2 className="text-lg font-bold flex items-center gap-2">
              <span>🤖</span> AI アドバイス
            </h2>
          }
        >
          <div className="bg-gradient-to-r from-indigo-50 to-blue-50 p-6 rounded-lg">
            <p className="text-gray-800 leading-relaxed">
              {summary.advice ||
                '食事情報がまだ記録されていません。食事を記録することで、AIがアドバイスを提供します。'}
            </p>
          </div>
        </Card>

        {/* 詳細表示 */}
        <Card header={<h2 className="text-lg font-bold">栄養素詳細</h2>}>
          <div className="space-y-3">
            <div className="flex justify-between p-3 bg-gray-50 rounded">
              <span className="text-gray-600">カロリー</span>
              <span className="font-semibold">{Math.round(summary.totalCalories)} kcal</span>
            </div>
            <div className="flex justify-between p-3 bg-red-50 rounded">
              <span className="text-gray-600">タンパク質</span>
              <span className="font-semibold text-red-600">
                {Math.round(summary.totalProtein)}g
              </span>
            </div>
            <div className="flex justify-between p-3 bg-yellow-50 rounded">
              <span className="text-gray-600">脂質</span>
              <span className="font-semibold text-yellow-600">
                {Math.round(summary.totalFat)}g
              </span>
            </div>
            <div className="flex justify-between p-3 bg-green-50 rounded">
              <span className="text-gray-600">炭水化物</span>
              <span className="font-semibold text-green-600">
                {Math.round(summary.totalCarbs)}g
              </span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

export const getServerSideProps: GetServerSideProps = requireAuth(
  async (context) => {
    return { props: {} }
  }
)
