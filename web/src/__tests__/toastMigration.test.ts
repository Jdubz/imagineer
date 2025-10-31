/**
 * Toast Migration Anti-Pattern Tests
 *
 * These tests enforce that the old custom toast system has been completely
 * removed and replaced with shadcn/ui toast throughout the application.
 */

/* eslint-disable @typescript-eslint/no-unsafe-call */

import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'fs'
import { join } from 'path'

const SRC_DIR = join(__dirname, '..')

/**
 * Recursively get all TypeScript/JavaScript files in a directory
 */
function getAllSourceFiles(dir: string, files: string[] = []): string[] {
  const entries = readdirSync(dir)

  for (const entry of entries) {
    const fullPath = join(dir, entry)
    const stat = statSync(fullPath)

    if (stat.isDirectory()) {
      // Skip node_modules, dist, and test directories
      if (!['node_modules', 'dist', 'build', '__tests__', 'test'].includes(entry)) {
        getAllSourceFiles(fullPath, files)
      }
    } else if (/\.(ts|tsx|js|jsx)$/.test(entry)) {
      files.push(fullPath)
    }
  }

  return files
}

describe('Toast Migration - Anti-Pattern Tests', () => {
  const allSourceFiles = getAllSourceFiles(SRC_DIR)

  it('should not import from the old useToast hook path', () => {
    const violations: string[] = []

    for (const file of allSourceFiles) {
      const content = readFileSync(file, 'utf-8')

      // Check for old import pattern
      const oldImportPattern = /from\s+['"]\.\.?\/.*\/useToast['"]/g
      const oldHookPath = /from\s+['"]\.\.?\/hooks\/useToast['"]/g

      if (oldImportPattern.test(content) || oldHookPath.test(content)) {
        // Make sure it's not the new use-toast
        if (!content.includes('use-toast')) {
          violations.push(file.replace(SRC_DIR, ''))
        }
      }
    }

    expect(violations).toEqual([])
  })

  it('should not import ToastContainer component', () => {
    const violations: string[] = []

    for (const file of allSourceFiles) {
      const content = readFileSync(file, 'utf-8')

      if (content.includes('ToastContainer') && !file.includes('__tests__')) {
        violations.push(file.replace(SRC_DIR, ''))
      }
    }

    expect(violations).toEqual([])
  })

  it('should not import ToastProvider context', () => {
    const violations: string[] = []

    for (const file of allSourceFiles) {
      const content = readFileSync(file, 'utf-8')

      // Exclude shadcn UI components which legitimately use ToastProvider
      if (
        content.includes('ToastProvider') &&
        !file.includes('__tests__') &&
        !file.includes('/ui/toast.tsx') &&
        !file.includes('/ui/toaster.tsx')
      ) {
        violations.push(file.replace(SRC_DIR, ''))
      }
    }

    expect(violations).toEqual([])
  })

  it('should use shadcn/ui Toaster component in App.tsx', () => {
    const appFile = join(SRC_DIR, 'App.tsx')
    const content = readFileSync(appFile, 'utf-8')

    // Should import from shadcn/ui
    expect(content).toMatch(/import.*Toaster.*from.*['"]\.\/components\/ui\/toaster['"]/)

    // Should render Toaster component
    expect(content).toContain('<Toaster />')
  })

  it('should use new toast API pattern (toast function, not methods)', () => {
    const violations: string[] = []

    for (const file of allSourceFiles) {
      const content = readFileSync(file, 'utf-8')

      // Check for old method patterns
      const oldPatterns = [
        /toast\.success\(/,
        /toast\.error\(/,
        /toast\.warning\(/,
        /toast\.info\(/,
      ]

      for (const pattern of oldPatterns) {
        if (pattern.test(content) && !file.includes('__tests__')) {
          violations.push(`${file.replace(SRC_DIR, '')}: uses old toast API`)
          break
        }
      }
    }

    expect(violations).toEqual([])
  })

  it('should destructure toast from useToast hook', () => {
    const violations: string[] = []

    for (const file of allSourceFiles) {
      const content = readFileSync(file, 'utf-8')

      // If file uses useToast, it should destructure { toast }
      if (content.includes('useToast()')) {
        // Check if it's using the old pattern
        const oldPattern = /const\s+toast\s*=\s*useToast\(\)/

        if (oldPattern.test(content) && !file.includes('__tests__')) {
          // Make sure it's not the new pattern with destructuring
          if (!content.includes('const { toast } = useToast()')) {
            violations.push(file.replace(SRC_DIR, ''))
          }
        }
      }
    }

    expect(violations).toEqual([])
  })

  it('should import from use-toast, not useToast', () => {
    const violations: string[] = []

    for (const file of allSourceFiles) {
      const content = readFileSync(file, 'utf-8')

      // Look for useToast imports
      if (content.includes('useToast')) {
        // Should be from use-toast
        if (!content.includes('use-toast') && !file.includes('use-toast.ts')) {
          violations.push(file.replace(SRC_DIR, ''))
        }
      }
    }

    expect(violations).toEqual([])
  })
})

describe('Toast Migration - File Deletion Verification', () => {
  it('should have deleted Toast.tsx', () => {
    const toastFile = join(SRC_DIR, 'components', 'Toast.tsx')

    expect(() => {
      readFileSync(toastFile)
    }).toThrow()
  })

  it('should have deleted ToastContext.tsx', () => {
    const contextFile = join(SRC_DIR, 'contexts', 'ToastContext.tsx')

    expect(() => {
      readFileSync(contextFile)
    }).toThrow()
  })

  it('should have deleted hooks/useToast.ts', () => {
    const hookFile = join(SRC_DIR, 'hooks', 'useToast.ts')

    expect(() => {
      readFileSync(hookFile)
    }).toThrow()
  })

  it('should have deleted Toast.css', () => {
    const cssFile = join(SRC_DIR, 'styles', 'Toast.css')

    expect(() => {
      readFileSync(cssFile)
    }).toThrow()
  })

  it('should still have shadcn use-toast hook', () => {
    const newHookFile = join(SRC_DIR, 'hooks', 'use-toast.ts')

    expect(() => {
      readFileSync(newHookFile)
    }).not.toThrow()
  })

  it('should still have shadcn toast components', () => {
    const toastComponent = join(SRC_DIR, 'components', 'ui', 'toast.tsx')
    const toasterComponent = join(SRC_DIR, 'components', 'ui', 'toaster.tsx')

    expect(() => {
      readFileSync(toastComponent)
    }).not.toThrow()

    expect(() => {
      readFileSync(toasterComponent)
    }).not.toThrow()
  })
})

describe('Toast API Usage Pattern Tests', () => {
  const criticalFiles = [
    'contexts/AppContext.tsx', // App.tsx now uses AppContext which has toast
    'components/GenerateForm.tsx',
    'components/AlbumsTab.tsx',
    'components/QueueTab.tsx',
    'contexts/BugReportContext.tsx',
  ]

  for (const file of criticalFiles) {
    it(`${file} should use correct toast API pattern`, () => {
      const filePath = join(SRC_DIR, file)
      const content = readFileSync(filePath, 'utf-8')

      // Should import from use-toast
      if (content.includes('toast') && content.includes('useToast')) {
        expect(content).toMatch(/from.*['"].*use-toast['"]/)
      }

      // Should destructure { toast }
      if (content.includes('useToast')) {
        expect(content).toMatch(/const\s*{\s*toast\s*}\s*=\s*useToast\(\)/)
      }

      // Should use new API format: toast({ title, description, variant })
      if (content.includes('toast({')) {
        // At least one toast call should follow the pattern
        expect(content).toMatch(/toast\(\{\s*title:/m)
      }
    })
  }
})
