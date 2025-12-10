import React, { useEffect, useState } from 'react'
import { GetServerSideProps } from 'next'
import Link from 'next/link'
import { Card, Input, Button, Alert, Loading } from '@/components'
import { api } from '@/lib/api-client'
import { requireAuth } from '@/lib/auth-middleware'

interface UserProfile {
  id: string
  name: string
  email: string
  age: number
  gender: 'male' | 'female'
  height: number
  weight: number
  activityLevel: string
  tdee: number
}

export default function Profile() {
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [formData, setFormData] = useState<Partial<UserProfile>>({})

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await api.getProfile()
        setProfile(data)
        setFormData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'プロフィールの読み込みに失敗しました')
      } finally {
        setLoading(false)
      }
    }

    fetchProfile()
  }, [])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'age' || name === 'height' || name === 'weight' ? parseFloat(value) : value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const updated = await api.updateProfile(formData)
      setProfile(updated)
      setSuccess('プロフィールを更新しました')
      setIsEditing(false)
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新に失敗しました')
    }
  }

  if (loading) {
    return <Loading message="プロフィールを読み込み中..." fullScreen />
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-2xl mx-auto">
          <Alert type="error" message="プロフィールが見つかりません" />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto">
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

        {success && (
          <Alert
            type="success"
            message={success}
            onClose={() => setSuccess(null)}
          />
        )}

        {/* プロフィールカード */}
        <Card
          header={
            <div className="flex justify-between items-center">
              <h1 className="text-2xl font-bold text-gray-900">プロフィール</h1>
              {!isEditing && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsEditing(true)}
                >
                  編集
                </Button>
              )}
            </div>
          }
        >
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input
                label="名前"
                name="name"
                value={formData.name || ''}
                onChange={handleInputChange}
                disabled={!isEditing}
              />
              <Input
                label="メール"
                name="email"
                type="email"
                value={formData.email || ''}
                disabled
              />

              <Input
                label="年齢"
                name="age"
                type="number"
                value={formData.age || ''}
                onChange={handleInputChange}
                disabled={!isEditing}
              />

              <select
                name="gender"
                value={formData.gender || ''}
                onChange={handleInputChange}
                disabled={!isEditing}
                className={`px-4 py-2 border rounded-lg ${
                  isEditing ? '' : 'bg-gray-100 cursor-not-allowed'
                }`}
              >
                <option value="">性別を選択</option>
                <option value="male">男性</option>
                <option value="female">女性</option>
              </select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input
                label="身長 (cm)"
                name="height"
                type="number"
                value={formData.height || ''}
                onChange={handleInputChange}
                disabled={!isEditing}
              />
              <Input
                label="体重 (kg)"
                name="weight"
                type="number"
                value={formData.weight || ''}
                onChange={handleInputChange}
                disabled={!isEditing}
              />
            </div>

            <div>
              <select
                name="activityLevel"
                value={formData.activityLevel || ''}
                onChange={handleInputChange}
                disabled={!isEditing}
                className={`w-full px-4 py-2 border rounded-lg ${
                  isEditing ? '' : 'bg-gray-100 cursor-not-allowed'
                }`}
              >
                <option value="">活動レベルを選択</option>
                <option value="sedentary">ほぼ運動しない</option>
                <option value="light">軽い運動</option>
                <option value="moderate">中程度の運動</option>
                <option value="active">活発な運動</option>
                <option value="very_active">非常に活発な運動</option>
              </select>
            </div>

            {/* TDEE表示 */}
            <div className="bg-indigo-50 p-4 rounded-lg">
              <p className="text-gray-600 mb-2">1日の推奨カロリー（TDEE）</p>
              <p className="text-3xl font-bold text-indigo-600">{profile.tdee} kcal</p>
            </div>

            {isEditing && (
              <div className="flex gap-4 pt-4">
                <Button type="submit" variant="primary">
                  保存
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setIsEditing(false)
                    setFormData(profile)
                  }}
                >
                  キャンセル
                </Button>
              </div>
            )}
          </form>
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
