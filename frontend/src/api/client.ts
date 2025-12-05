/**
 * APIクライアント
 *
 * バックエンドAPIとの通信を担当
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type { ApiError } from '../types/api';

// API Gateway URLは環境変数から取得
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000';

/**
 * Axiosインスタンスを作成
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000, // 30秒
  });

  // リクエストインターセプター: 認証トークンを追加
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      const token = localStorage.getItem('idToken');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // レスポンスインターセプター: エラーハンドリング
  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError<ApiError>) => {
      if (error.response) {
        // サーバーがエラーレスポンスを返した場合
        const apiError = error.response.data;
        console.error('API Error:', apiError);

        // 401エラーの場合、認証トークンをクリア
        if (error.response.status === 401) {
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          localStorage.removeItem('idToken');
          // ログイン画面にリダイレクト（ここではイベント発火のみ）
          window.dispatchEvent(new Event('unauthorized'));
        }

        return Promise.reject(apiError);
      } else if (error.request) {
        // リクエストは送信されたがレスポンスがない
        console.error('No response received:', error.request);
        return Promise.reject({
          error: {
            code: 'NETWORK_ERROR',
            message: 'ネットワークエラーが発生しました',
          },
        });
      } else {
        // リクエスト設定中にエラーが発生
        console.error('Request setup error:', error.message);
        return Promise.reject({
          error: {
            code: 'REQUEST_ERROR',
            message: 'リクエストエラーが発生しました',
          },
        });
      }
    }
  );

  return client;
};

export const apiClient = createApiClient();

/**
 * 認証トークンを設定
 */
export const setAuthTokens = (accessToken: string, refreshToken: string, idToken: string) => {
  localStorage.setItem('accessToken', accessToken);
  localStorage.setItem('refreshToken', refreshToken);
  localStorage.setItem('idToken', idToken);
};

/**
 * 認証トークンをクリア
 */
export const clearAuthTokens = () => {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('idToken');
};

/**
 * 認証トークンを取得
 */
export const getAuthTokens = () => {
  return {
    accessToken: localStorage.getItem('accessToken'),
    refreshToken: localStorage.getItem('refreshToken'),
    idToken: localStorage.getItem('idToken'),
  };
};
