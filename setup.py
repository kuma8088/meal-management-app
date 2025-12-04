"""
食事管理アプリケーション セットアップ
"""
from setuptools import setup, find_packages

setup(
    name="meal-management-app",
    version="0.1.0",
    description="AWS サーバレスアーキテクチャを活用した食事管理アプリケーション",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "boto3>=1.34.0",
        "botocore>=1.34.0",
        "python-dateutil>=2.8.2",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "hypothesis>=6.92.0",
            "moto>=4.2.10",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "isort>=5.13.2",
            "pylint>=3.0.3",
            "mypy>=1.7.1",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
    ],
)
