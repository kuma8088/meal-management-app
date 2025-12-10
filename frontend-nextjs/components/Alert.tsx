import React from 'react'

interface AlertProps {
  type: 'success' | 'error' | 'warning' | 'info'
  title?: string
  message: string
  onClose?: () => void
}

const alertConfig = {
  success: {
    bg: 'bg-green-50',
    border: 'border-green-200',
    icon: '✅',
    textColor: 'text-green-800',
  },
  error: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: '❌',
    textColor: 'text-red-800',
  },
  warning: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    icon: '⚠️',
    textColor: 'text-yellow-800',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: 'ℹ️',
    textColor: 'text-blue-800',
  },
}

export const Alert: React.FC<AlertProps> = ({
  type,
  title,
  message,
  onClose,
}) => {
  const config = alertConfig[type]

  return (
    <div
      className={`${config.bg} border ${config.border} rounded-lg p-4 flex items-start gap-3`}
      role="alert"
    >
      <span className="text-xl flex-shrink-0">{config.icon}</span>
      <div className="flex-1">
        {title && (
          <h3 className={`${config.textColor} font-semibold mb-1`}>
            {title}
          </h3>
        )}
        <p className={`${config.textColor} text-sm`}>{message}</p>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className={`${config.textColor} flex-shrink-0 hover:opacity-70`}
        >
          ✕
        </button>
      )}
    </div>
  )
}
