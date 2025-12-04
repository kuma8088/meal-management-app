# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- プロジェクト構成の初期セットアップ
- Terraform インフラストラクチャコード
  - DynamoDB テーブル定義（Users, Meals, Foods, Goals, AdviceUsage）
  - S3 バケット定義（terraform-state, food-master, barcode-images, frontend）
  - プロバイダー設定とバックエンド設定
  - 変数定義と出力定義
- Lambda 関数のディレクトリ構造
- テストフレームワークのセットアップ（pytest, hypothesis）
- 開発ツールの設定
  - Makefile
  - セットアップスクリプト
  - デプロイスクリプト
- ドキュメント
  - README.md
  - ARCHITECTURE.md
  - CHANGELOG.md

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [0.1.0] - 2024-12-02

### Added

- 初期プロジェクトセットアップ
