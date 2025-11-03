import React from 'react'

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
    <div className="relative z-[10000]">
      <a
        href="#main-content"
        className="absolute -top-24 left-0 px-6 py-4 bg-blue-600 text-white text-base font-semibold no-underline rounded-br shadow-xl transition-[top] duration-200 z-[10001] focus:top-0 focus:outline focus:outline-3 focus:outline-yellow-400 focus:outline-offset-2 hover:bg-blue-700 hover:underline"
      >
        Skip to main content
      </a>
      <a
        href="#tabs-navigation"
        className="absolute -top-24 right-0 left-auto px-6 py-4 bg-blue-600 text-white text-base font-semibold no-underline rounded-bl shadow-xl transition-[top] duration-200 z-[10001] focus:top-0 focus:outline focus:outline-3 focus:outline-yellow-400 focus:outline-offset-2 hover:bg-blue-700 hover:underline"
      >
        Skip to navigation
      </a>
    </div>
  )
}

export default SkipNav
