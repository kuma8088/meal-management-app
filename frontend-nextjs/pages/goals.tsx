import React, { useEffect, useState } from 'react'
import { GetServerSideProps } from 'next'
import Link from 'next/link'
import { Card, Input, Button, Alert, Loading } from '@/components'
import { api } from '@/lib/api-client'
import { requireAuth } from '@/lib/auth-middleware'

interface Goal {
  id: string
  targetWeight: number
  currentWeight: number
  targetDate: string
  createdAt: string
  status: 'active' | 'completed' | 'archived'
}

export default function Goals() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [formData, setFormData] = useState({
    targetWeight: '',
    targetDate: '',
  })

  useEffect(() => {
    const fetchGoals = async () => {
      try {
        const data = await api.getGoals()
        setGoals(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '目標の読み込みに失敗しました')
      } finally {
        setLoading(false)
      }
    }

    fetchGoals()
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'targetWeight' ? parseFloat(value) : value,
    }))
  }

  const handleCreateGoal = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const newGoal = await api.createGoal(formData)
      setGoals((prev) => [...prev, newGoal])
      setFormData({ targetWeight: '', targetDate: '' })
      setIsCreating(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : '目標の作成に失敗しました')
    }
  }

  if (loading) {
    return <Loading message="目標を読み込み中..." fullScreen />
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto">
        {/* ヘッダー */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/home" className="text-indigo-600 hover:text-indigo-700 font-semibold">
              ← ホームに戻る
            </Link>
          </div>
          {!isCreating && (
            <Button variant="primary" onClick={() => setIsCreating(true)}>
              + 新しい目標を作成
            </Button>
          )}
        </div>

        {error && (
          <Alert
            type="error"
            message={error}
            onClose={() => setError(null)}
          />
        )}

        {/* 新規作成フォーム */}
        {isCreating && (
          <Card className="mb-6" header={<h2 className="text-lg font-bold">新しい目標を作成</h2>}>
            <form onSubmit={handleCreateGoal} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="目標体重 (kg)"
                  name="targetWeight"
                  type="number"
                  placeholder="60"
                  step="0.1"
                  required
                  value={formData.targetWeight}
                  onChange={handleInputChange}
                />
                <Input
                  label="目標日付"
                  name="targetDate"
                  type="date"
                  required
                  value={formData.targetDate}
                  onChange={handleInputChange}
                />
              </div>
              <div className="flex gap-4">
                <Button type="submit" variant="primary">
                  作成
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setIsCreating(false)
                    setFormData({ targetWeight: '', targetDate: '' })
                  }}
                >
                  キャンセル
                </Button>
              </div>
            </form>
          </Card>
        )}

        {/* 目標一覧 */}
        <h1 className="text-2xl font-bold text-gray-900 mb-6">目標</h1>
        {goals.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <p className="text-gray-600 mb-4">目標がまだ設定されていません</p>
              <Button onClick={() => setIsCreating(true)}>
                最初の目標を作成
              </Button>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {goals.map((goal) => (
              <Card
                key={goal.id}
                header={
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-gray-900">
                      目標体重: {goal.targetWeight} kg
                    </h3>
                    <span
                      className={`text-sm px-3 py-1 rounded-full ${
                        goal.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : goal.status === 'active'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {goal.status === 'completed' ? '達成' : goal.status === 'active' ? '進行中' : 'アーカイブ'}
                    </span>
                  </div>
                }
              >
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">現在の体重</span>
                    <span className="font-semibold">{goal.currentWeight} kg</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">目標日付</span>
                    <span className="font-semibold">
                      {new Date(goal.targetDate).toLocaleDateString('ja-JP')}
                    </span>
                  </div>
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-gray-600 text-sm">進捗</span>
                      <span className="text-sm font-semibold">
                        {Math.round(
                          ((goal.currentWeight - goal.targetWeight) /
                            (goal.currentWeight - goal.targetWeight)) *
                            100
                        )}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-indigo-600 h-2 rounded-full"
                        style={{
                          width: `${Math.min(
                            ((goal.currentWeight - goal.targetWeight) /
                              Math.abs(goal.currentWeight - goal.targetWeight)) *
                              100,
                            100
                          )}%`,
                        }}
                      />
                    </div>
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
