/**
 * ユーザープロフィール設定ページ
 */

import React, { useState, useEffect } from 'react';
import { useUnifiedAuth } from '../contexts/UnifiedAuthContext';
import { getUserProfile, createUserProfile, updateUserProfile } from '../api/users';
import ProfileForm from '../components/ProfileForm';
import type { UserProfile, CreateUserProfileRequest } from '../types/api';
import './ProfilePage.css';

const ProfilePage: React.FC = () => {
  const { user, loading: authLoading } = useUnifiedAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  /**
   * プロフィールを読み込み
   */
  useEffect(() => {
    const loadProfile = async () => {
      // AuthContextの初期化を待つ
      if (authLoading) {
        return;
      }

      if (!user) return;

      try {
        setLoading(true);
        const data = await getUserProfile(user.userId);
        setProfile(data);
      } catch (err: any) {
        // プロフィールが存在しない場合は新規作成モード
        if (err.error?.code === 'NOT_FOUND' || err.error?.code === 'RESOURCE_NOT_FOUND') {
          setProfile(null);
        } else {
          setError('プロフィールの読み込みに失敗しました');
          console.error('Failed to load profile:', err);
        }
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, [user, authLoading]);

  /**
   * プロフィールを保存
   */
  const handleSave = async (data: CreateUserProfileRequest) => {
    if (!user) return;

    try {
      setError('');
      setSuccessMessage('');
      setLoading(true);

      let savedProfile: UserProfile;
      if (profile) {
        // 更新
        savedProfile = await updateUserProfile(user.userId, data);
        setSuccessMessage('プロフィールを更新しました');
      } else {
        // 新規作成
        savedProfile = await createUserProfile(data);
        setSuccessMessage('プロフィールを作成しました');
      }

      setProfile(savedProfile);
    } catch (err: any) {
      setError(err.error?.message || 'プロフィールの保存に失敗しました');
      console.error('Failed to save profile:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !profile) {
    return (
      <div className="profile-page">
        <div className="loading">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-container">
        <h1 className="page-title">プロフィール設定</h1>

        {error && <div className="error-message">{error}</div>}
        {successMessage && <div className="success-message">{successMessage}</div>}

        <ProfileForm
          initialData={profile || undefined}
          onSubmit={handleSave}
          loading={loading}
        />
      </div>
    </div>
  );
};

export default ProfilePage;
