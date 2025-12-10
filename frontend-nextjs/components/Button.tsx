import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', isLoading, className, ...props }, ref) => {
    const baseClasses = 'font-semibold rounded-lg transition duration-200 flex items-center justify-center gap-2'

    const variantClasses = {
      primary: 'bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-indigo-400',
      secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-900 disabled:bg-gray-100',
      danger: 'bg-red-600 hover:bg-red-700 text-white disabled:bg-red-400',
    }

    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-base',
      lg: 'px-6 py-3 text-lg',
    }

    return (
      <button
        ref={ref}
        className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className || ''}`}
        disabled={isLoading || props.disabled}
        {...props}
      >
        {isLoading && <span className="inline-block animate-spin">⏳</span>}
        {props.children}
      </button>
    )
  }
)

Button.displayName = 'Button'
