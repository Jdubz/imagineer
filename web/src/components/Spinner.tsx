import React from 'react'
import '../styles/Spinner.css'

interface SpinnerProps {
  size?: 'small' | 'medium' | 'large'
  message?: string
}

/**
 * Reusable loading spinner component
 * Shows an animated spinner with optional message
 */
const Spinner: React.FC<SpinnerProps> = ({ size = 'medium', message }) => {
  return (
    <div className={`spinner-container spinner-${size}`}>
      <div className="spinner" aria-label="Loading" role="status">
        <div className="spinner-circle"></div>
      </div>
      {message && <p className="spinner-message">{message}</p>}
    </div>
  )
}

export default Spinner
