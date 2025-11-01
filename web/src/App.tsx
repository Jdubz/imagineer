import React, { useEffect, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import './styles/App.css'
import SkipNav from './components/SkipNav'
import Tabs from './components/Tabs'
import ErrorBoundaryWithReporting from './components/ErrorBoundaryWithReporting'
import { Toaster } from './components/ui/toaster'
import Spinner from './components/Spinner'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { useKeyboardShortcut } from './hooks/useKeyboardShortcut'
import type { Tab } from './types/models'
import { BugReportProvider, useBugReporter } from './contexts/BugReportContext'
import { AppProvider, useApp } from './contexts/AppContext'
import SettingsMenu from './components/SettingsMenu'
import AuthButton from './components/AuthButton'

// Lazy load tab components for code splitting
const GenerateTab = lazy(() => import('./components/GenerateTab'))
const GalleryTab = lazy(() => import('./components/GalleryTab'))
const AlbumsTab = lazy(() => import('./components/AlbumsTab'))
const ScrapingTab = lazy(() => import('./components/ScrapingTab'))
const TrainingTab = lazy(() => import('./components/TrainingTab'))
const LorasTab = lazy(() => import('./components/LorasTab'))
const QueueTab = lazy(() => import('./components/QueueTab'))

const AppContent: React.FC = () => {
  const location = useLocation()
  const { user, logout, setUser } = useAuth()
  const { openBugReport, registerCollector } = useBugReporter()
  const { generation, gallery, nsfwPreference, setNsfwPreference } = useApp()

  // Tab configuration
  const tabs: Tab[] = [
    { id: 'generate', label: 'Generate', icon: '✨' },
    { id: 'gallery', label: 'Gallery', icon: '🖼️' },
    { id: 'albums', label: 'Albums', icon: '📁' },
    { id: 'scraping', label: 'Scraping', icon: '🕷️' },
    { id: 'training', label: 'Training', icon: '🚀' },
    { id: 'queue', label: 'Queue', icon: '📋' },
    { id: 'loras', label: 'LoRAs', icon: '🎨' }
  ]

  // Get active tab from URL
  const activeTab = location.pathname.slice(1) || 'generate'

  // Register Ctrl+Shift+B keyboard shortcut for bug reporting (admin only)
  useKeyboardShortcut({
    key: 'b',
    ctrlKey: true,
    shiftKey: true,
    enabled: user?.role === 'admin',
    callback: openBugReport,
  })

  // Register bug report data collector
  useEffect(() => {
    const unregister = registerCollector('application_state', () => {
      const imagePreview = gallery.images.slice(0, 5).map(({ filename, created, metadata }) => ({
        filename,
        created,
        model: metadata?.model,
        seed: metadata?.seed,
      }))

      const batchPreview = gallery.batches.slice(0, 5).map(({ batch_id, image_count, created }) => ({
        batch_id,
        image_count,
        created,
      }))

      const jobSnapshot = generation.currentJob
        ? {
            id: generation.currentJob.id,
            status: generation.currentJob.status,
            queue_position: generation.currentJob.queue_position,
            submitted_at: generation.currentJob.submitted_at ?? generation.currentJob.created ?? null,
          }
        : null

      return {
        config_loaded: generation.config !== null,
        config_version: generation.config?.version,
        images_loaded: gallery.images.length,
        batches_loaded: gallery.batches.length,
        current_tab: activeTab,
        loading_state: {
          generation: generation.loading,
          images: gallery.loadingImages,
          batches: gallery.loadingBatches,
        },
        current_job: jobSnapshot,
        queue_position: generation.queuePosition,
        nsfw_preference: nsfwPreference,
        images_preview: imagePreview,
        batches_preview: batchPreview,
      }
    })

    return () => {
      unregister()
    }
  }, [
    registerCollector,
    generation.config,
    generation.loading,
    generation.currentJob,
    generation.queuePosition,
    gallery.images,
    gallery.batches,
    gallery.loadingImages,
    gallery.loadingBatches,
    nsfwPreference,
    activeTab,
  ])

  return (
    <div className="App">
      <SkipNav />
      <Toaster />
      <header className="header">
        <div className="header-content">
          <div className="header-title">
            <h1>✨ Imagineer</h1>
            <p>AI Image Generation Toolkit</p>
          </div>
          <div className="header-actions">
            {user ? (
              <SettingsMenu
                user={user}
                onLogout={logout}
                onNsfwChange={setNsfwPreference}
                nsfwPreference={nsfwPreference}
              />
            ) : (
              <AuthButton onAuthChange={setUser} />
            )}
          </div>
        </div>
      </header>

      <div className="container">
        <nav id="tabs-navigation" aria-label="Main navigation">
          <Tabs tabs={tabs} activeTab={activeTab} />
        </nav>

        <main id="main-content" className="main-content">
          <Suspense fallback={<Spinner size="large" message="Loading..." />}>
            <Routes>
              <Route path="/" element={<Navigate to="/generate" replace />} />
              <Route
                path="/generate"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Generate Tab">
                    <GenerateTab isAdmin={user?.role === 'admin'} />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/gallery"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Gallery Tab">
                    <GalleryTab />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/albums"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Albums Tab">
                    <AlbumsTab isAdmin={user?.role === 'admin'} />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/scraping"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Scraping Tab">
                    <ScrapingTab isAdmin={user?.role === 'admin'} />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/training"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Training Tab">
                    <TrainingTab isAdmin={user?.role === 'admin'} />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/queue"
                element={
                  <ErrorBoundaryWithReporting boundaryName="Queue Tab">
                    <QueueTab />
                  </ErrorBoundaryWithReporting>
                }
              />
              <Route
                path="/loras"
                element={
                  <ErrorBoundaryWithReporting boundaryName="LoRAs Tab">
                    <LorasTab />
                  </ErrorBoundaryWithReporting>
                }
              />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  )
}

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <BugReportProvider>
          <AppProvider>
            <AppContent />
          </AppProvider>
        </BugReportProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
