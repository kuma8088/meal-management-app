/**
 * ユーザーAPI
 */

import { apiClient } from './client';
import type {
  UserProfile,
  CreateUserProfileRequest,
  UpdateUserProfileRequest,
} from '../types/api';

/**
 * ユーザープロフィールを作成
 */
export const createUserProfile = async (
  data: CreateUserProfileRequest
): Promise<UserProfile> => {
  const response = await apiClient.post<UserProfile>('/users', data);
  return response.data;
};

/**
 * ユーザープロフィールを取得
 */
export const getUserProfile = async (userId: string): Promise<UserProfile> => {
  const response = await apiClient.get<UserProfile>(`/users/${userId}`);
  return response.data;
};

/**
 * ユーザープロフィールを更新
 */
export const updateUserProfile = async (
  userId: string,
  data: UpdateUserProfileRequest
): Promise<UserProfile> => {
  const response = await apiClient.put<UserProfile>(`/users/${userId}`, data);
  return response.data;
};
