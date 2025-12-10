import React, { useState } from 'react'
import { GetServerSideProps } from 'next'
import { useRouter } from 'next/router'
import Link from 'next/link'
import { Card, Input, Button, Alert, Loading } from '@/components'
import { api } from '@/lib/api-client'
import { requireAuth } from '@/lib/auth-middleware'

interface FoodItem {
  id: string
  name: string
  calories: number
  protein: number
  fat: number
  carbs: number
}

interface MealFood {
  name: string
  quantity: number
  unit: string
  calories: number
  protein: number
  fat: number
  carbs: number
}

export default function NewMeal() {
  const router = useRouter()
  const [foods, setFoods] = useState<MealFood[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<FoodItem[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [newFood, setNewFood] = useState({
    quantity: 1,
    unit: 'g',
  })

  // 食品検索
  const handleSearch = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value
    setSearchQuery(query)

    if (query.length < 2) {
      setSearchResults([])
      return
    }

    setIsSearching(true)
    try {
      const results = await api.searchFoods(query, 10)
      setSearchResults(results)
    } catch (err) {
      setError(err instanceof Error ? err.message : '食品検索に失敗しました')
    } finally {
      setIsSearching(false)
    }
  }

  // 食品を食事に追加
  const handleAddFood = (food: FoodItem) => {
    const quantity = parseFloat(String(newFood.quantity)) || 1
    const multiplier = quantity / 100

    const mealFood: MealFood = {
      name: food.name,
      quantity,
      unit: newFood.unit,
      calories: Math.round(food.calories * multiplier),
      protein: Math.round(food.protein * multiplier),
      fat: Math.round(food.fat * multiplier),
      carbs: Math.round(food.carbs * multiplier),
    }

    setFoods((prev) => [...prev, mealFood])
    setSearchQuery('')
    setSearchResults([])
    setNewFood({ quantity: 1, unit: 'g' })
  }

  // 食品を削除
  const handleRemoveFood = (index: number) => {
    setFoods((prev) => prev.filter((_, i) => i !== index))
  }

  // 食事を保存
  const handleSaveMeal = async (e: React.FormEvent) => {
    e.preventDefault()

    if (foods.length === 0) {
      setError('最低1つの食品を追加してください')
      return
    }

    setIsSubmitting(true)
    try {
      await api.createMeal({
        foods: foods.map((f) => ({
          name: f.name,
          quantity: f.quantity,
          unit: f.unit,
        })),
        totalCalories: foods.reduce((sum, f) => sum + f.calories, 0),
        totalProtein: foods.reduce((sum, f) => sum + f.protein, 0),
        totalFat: foods.reduce((sum, f) => sum + f.fat, 0),
        totalCarbs: foods.reduce((sum, f) => sum + f.carbs, 0),
      })

      router.push('/meals')
    } catch (err) {
      setError(err instanceof Error ? err.message : '食事の保存に失敗しました')
    } finally {
      setIsSubmitting(false)
    }
  }

  const totalCalories = foods.reduce((sum, f) => sum + f.calories, 0)
  const totalProtein = foods.reduce((sum, f) => sum + f.protein, 0)
  const totalFat = foods.reduce((sum, f) => sum + f.fat, 0)
  const totalCarbs = foods.reduce((sum, f) => sum + f.carbs, 0)

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        {/* ヘッダー */}
        <div className="mb-6 flex items-center gap-4">
          <Link href="/meals" className="text-indigo-600 hover:text-indigo-700 font-semibold">
            ← 食事記録に戻る
          </Link>
        </div>

        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError(null)}
          />
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 食品検索パネル */}
          <Card className="lg:col-span-1 h-fit" header={<h2 className="text-lg font-bold">食品を検索</h2>}>
            <div className="space-y-4">
              <Input
                placeholder="食品名を入力"
                value={searchQuery}
                onChange={handleSearch}
                disabled={isSearching}
              />

              {isSearching && <Loading message="検索中..." />}

              {searchResults.length > 0 && (
                <div className="space-y-2 max-h-96 overflow-y-auto border rounded-lg p-2">
                  {searchResults.map((food) => (
                    <div
                      key={food.id}
                      className="p-3 bg-gray-50 rounded-lg cursor-pointer hover:bg-indigo-50 transition"
                      onClick={() => handleAddFood(food)}
                    >
                      <p className="font-semibold text-sm text-gray-900">{food.name}</p>
                      <p className="text-xs text-gray-600">
                        {food.calories} kcal / 100g
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {searchQuery && searchResults.length === 0 && !isSearching && (
                <p className="text-sm text-gray-500 text-center py-4">
                  該当する食品がありません
                </p>
              )}

              <div>
                <label className="text-sm text-gray-600 block mb-2">数量</label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    min="1"
                    step="0.1"
                    value={newFood.quantity}
                    onChange={(e) =>
                      setNewFood((prev) => ({
                        ...prev,
                        quantity: parseFloat(e.target.value) || 1,
                      }))
                    }
                  />
                  <select
                    value={newFood.unit}
                    onChange={(e) =>
                      setNewFood((prev) => ({
                        ...prev,
                        unit: e.target.value,
                      }))
                    }
                    className="px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="g">g</option>
                    <option value="ml">ml</option>
                    <option value="個">個</option>
                    <option value="枚">枚</option>
                  </select>
                </div>
              </div>
            </div>
          </Card>

          {/* 食事内容 */}
          <div className="lg:col-span-2 space-y-6">
            <Card header={<h2 className="text-lg font-bold">食事内容</h2>}>
              {foods.length === 0 ? (
                <div className="text-center py-8 text-gray-600">
                  <p>左のパネルから食品を追加してください</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {foods.map((food, index) => (
                    <div
                      key={index}
                      className="p-4 bg-gray-50 rounded-lg flex items-start justify-between"
                    >
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">
                          {food.name} {food.quantity}
                          {food.unit}
                        </h3>
                        <div className="text-xs text-gray-600 mt-2 grid grid-cols-4 gap-2">
                          <div>
                            カロリー: <span className="font-semibold">{food.calories}</span>{' '}
                            kcal
                          </div>
                          <div>
                            タンパク: <span className="font-semibold">{food.protein}</span> g
                          </div>
                          <div>
                            脂質: <span className="font-semibold">{food.fat}</span> g
                          </div>
                          <div>
                            炭水: <span className="font-semibold">{food.carbs}</span> g
                          </div>
                        </div>
                      </div>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleRemoveFood(index)}
                      >
                        削除
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* 合計栄養素 */}
            {foods.length > 0 && (
              <Card header={<h2 className="text-lg font-bold">合計栄養素</h2>}>
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <p className="text-gray-600 text-sm mb-2">カロリー</p>
                    <p className="text-3xl font-bold text-blue-600">
                      {Math.round(totalCalories)}
                    </p>
                    <p className="text-xs text-gray-600">kcal</p>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded-lg">
                    <p className="text-gray-600 text-sm mb-2">タンパク質</p>
                    <p className="text-3xl font-bold text-red-600">
                      {Math.round(totalProtein)}
                    </p>
                    <p className="text-xs text-gray-600">g</p>
                  </div>
                  <div className="text-center p-4 bg-yellow-50 rounded-lg">
                    <p className="text-gray-600 text-sm mb-2">脂質</p>
                    <p className="text-3xl font-bold text-yellow-600">
                      {Math.round(totalFat)}
                    </p>
                    <p className="text-xs text-gray-600">g</p>
                  </div>
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <p className="text-gray-600 text-sm mb-2">炭水化物</p>
                    <p className="text-3xl font-bold text-green-600">
                      {Math.round(totalCarbs)}
                    </p>
                    <p className="text-xs text-gray-600">g</p>
                  </div>
                </div>
              </Card>
            )}

            {/* アクションボタン */}
            <div className="flex gap-4">
              <Button
                variant="primary"
                onClick={handleSaveMeal}
                disabled={isSubmitting || foods.length === 0}
                isLoading={isSubmitting}
              >
                食事を保存
              </Button>
              <Link href="/meals" className="flex-1">
                <Button variant="secondary" className="w-full">
                  キャンセル
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export const getServerSideProps: GetServerSideProps = requireAuth(
  async (context) => {
    return { props: {} }
  }
)
