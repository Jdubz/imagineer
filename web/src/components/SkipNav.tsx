import React from 'react'
import '../styles/SkipNav.css'

/**
 * SkipNav component provides keyboard navigation shortcuts
 * to improve accessibility for screen reader and keyboard users.
 *
 * WCAG 2.1 AA Compliance:
 * - Allows users to skip repetitive navigation
 * - Visible on focus for keyboard users
 * - Hidden by default to avoid visual clutter
 */
const SkipNav: React.FC = () => {
  return (
    <div className="skip-nav">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <a href="#tabs-navigation" className="skip-link">
        Skip to navigation
      </a>
    </div>
  )
}

export default SkipNav
