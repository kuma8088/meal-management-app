import React, { useEffect, useState } from 'react'
import { GetServerSideProps } from 'next'
import Link from 'next/link'
import { Card, Button, Alert, Loading } from '@/components'
import { api } from '@/lib/api-client'
import { requireAuth } from '@/lib/auth-middleware'

interface Meal {
  id: string
  timestamp: string
  foods: Array<{
    name: string
    quantity: number
    unit: string
  }>
  totalCalories: number
  totalProtein: number
  totalFat: number
  totalCarbs: number
}

export default function Meals() {
  const [meals, setMeals] = useState<Meal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMeals = async () => {
      try {
        const data = await api.getMeals()
        setMeals(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '食事記録の読み込みに失敗しました')
      } finally {
        setLoading(false)
      }
    }

    fetchMeals()
  }, [])

  const handleDeleteMeal = async (id: string) => {
    if (!confirm('この食事記録を削除してもよろしいですか？')) {
      return
    }

    try {
      await api.deleteMeal(id)
      setMeals((prev) => prev.filter((meal) => meal.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err.message : '削除に失敗しました')
    }
  }

  if (loading) {
    return <Loading message="食事記録を読み込み中..." fullScreen />
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-6xl mx-auto">
        {/* ヘッダー */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/home" className="text-indigo-600 hover:text-indigo-700 font-semibold">
              ← ホームに戻る
            </Link>
          </div>
          <Link href="/meals/new">
            <Button variant="primary">+ 食事を記録</Button>
          </Link>
        </div>

        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError(null)}
          />
        )}

        {/* 食事記録一覧 */}
        <h1 className="text-2xl font-bold text-gray-900 mb-6">食事記録</h1>
        {meals.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <p className="text-gray-600 mb-4">食事記録がまだありません</p>
              <Link href="/meals/new">
                <Button variant="primary">最初の食事を記録</Button>
              </Link>
            </div>
          </Card>
        ) : (
          <div className="space-y-4">
            {meals.map((meal) => (
              <Card key={meal.id}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg text-gray-900 mb-2">
                      {new Date(meal.timestamp).toLocaleString('ja-JP')}
                    </h3>

                    {/* 食品一覧 */}
                    <div className="mb-4">
                      <p className="text-sm text-gray-600 mb-2">食品:</p>
                      <div className="space-y-1">
                        {meal.foods.map((food, idx) => (
                          <p key={idx} className="text-sm text-gray-700">
                            • {food.name} {food.quantity}
                            {food.unit}
                          </p>
                        ))}
                      </div>
                    </div>

                    {/* 栄養素情報 */}
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div className="bg-blue-50 p-3 rounded">
                        <p className="text-gray-600 text-xs mb-1">カロリー</p>
                        <p className="font-bold text-blue-600">
                          {Math.round(meal.totalCalories)} kcal
                        </p>
                      </div>
                      <div className="bg-red-50 p-3 rounded">
                        <p className="text-gray-600 text-xs mb-1">タンパク質</p>
                        <p className="font-bold text-red-600">
                          {Math.round(meal.totalProtein)} g
                        </p>
                      </div>
                      <div className="bg-yellow-50 p-3 rounded">
                        <p className="text-gray-600 text-xs mb-1">脂質</p>
                        <p className="font-bold text-yellow-600">
                          {Math.round(meal.totalFat)} g
                        </p>
                      </div>
                      <div className="bg-green-50 p-3 rounded">
                        <p className="text-gray-600 text-xs mb-1">炭水化物</p>
                        <p className="font-bold text-green-600">
                          {Math.round(meal.totalCarbs)} g
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* アクションボタン */}
                  <div className="flex gap-2 ml-4">
                    <Link href={`/meals/${meal.id}/edit`}>
                      <Button variant="secondary" size="sm">
                        編集
                      </Button>
                    </Link>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDeleteMeal(meal.id)}
                    >
                      削除
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export const getServerSideProps: GetServerSideProps = requireAuth(
  async (context) => {
    return { props: {} }
  }
)
