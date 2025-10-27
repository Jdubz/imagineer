import React, { useState, useEffect } from 'react'
import './styles/App.css'
import PasswordGate from './components/PasswordGate'
import AuthButton from './components/AuthButton'
import Tabs from './components/Tabs'
import GenerateTab from './components/GenerateTab'
import GalleryTab from './components/GalleryTab'
import AlbumsTab from './components/AlbumsTab'
import LorasTab from './components/LorasTab'
import QueueTab from './components/QueueTab'

function App() {
  const [config, setConfig] = useState(null)
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(false)
  const [currentJob, setCurrentJob] = useState(null)
  const [queuePosition, setQueuePosition] = useState(null)
  const [batches, setBatches] = useState([])
  const [activeTab, setActiveTab] = useState('generate')
  const [user, setUser] = useState(null)

  // Tab configuration
  const tabs = [
    { id: 'generate', label: 'Generate', icon: '✨' },
    { id: 'gallery', label: 'Gallery', icon: '🖼️' },
    { id: 'albums', label: 'Albums', icon: '📁' },
    { id: 'queue', label: 'Queue', icon: '📋' },
    { id: 'loras', label: 'LoRAs', icon: '🎨' }
  ]

  // Load config on mount
  useEffect(() => {
    fetchConfig()
    fetchImages()
    fetchBatches()
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const response = await fetch('/auth/me', {
        credentials: 'include'
      })
      const data = await response.json()

      if (data.authenticated) {
        setUser(data)
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error('Failed to check auth:', error)
      setUser(null)
    }
  }

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/config')
      const data = await response.json()
      setConfig(data)
    } catch (error) {
      console.error('Failed to fetch config:', error)
    }
  }

  const fetchImages = async () => {
    try {
      const response = await fetch('/api/outputs')
      const data = await response.json()
      setImages(data.images || [])
    } catch (error) {
      console.error('Failed to fetch images:', error)
    }
  }

  const fetchBatches = async () => {
    try {
      const response = await fetch('/api/batches')
      const data = await response.json()
      setBatches(data.batches || [])
    } catch (error) {
      console.error('Failed to fetch batches:', error)
    }
  }

  const handleGenerate = async (params) => {
    setLoading(true)
    setQueuePosition(null)
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      })

      if (response.status === 201) {
        // Job created successfully
        const result = await response.json()
        setCurrentJob(result)
        setQueuePosition(result.queue_position)

        // Poll for completion
        pollJobStatus(result.id)
      } else {
        const error = await response.json()
        alert('Failed to submit job: ' + error.error)
        setLoading(false)
      }
    } catch (error) {
      console.error('Failed to generate:', error)
      alert('Error submitting job')
      setLoading(false)
    }
  }

  const handleGenerateBatch = async (params) => {
    setLoading(true)
    try {
      const response = await fetch('/api/generate/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      })

      if (response.status === 201) {
        const result = await response.json()
        alert(`Batch generation started!\n${result.total_jobs} jobs queued for ${result.set_name}`)
        // Refresh batches list and switch to gallery tab
        fetchBatches()
        setActiveTab('gallery')
      } else {
        const error = await response.json()
        alert('Failed to submit batch: ' + error.error)
      }
    } catch (error) {
      console.error('Failed to generate batch:', error)
      alert('Error submitting batch')
    } finally {
      setLoading(false)
    }
  }

  const pollJobStatus = async (jobId) => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`/api/jobs/${jobId}`)
        const job = await response.json()

        // Update queue position
        if (job.queue_position !== undefined) {
          setQueuePosition(job.queue_position)
        }

        if (job.status === 'completed') {
          setLoading(false)
          setCurrentJob(null)
          setQueuePosition(null)
          fetchImages() // Refresh image grid
          fetchBatches() // Refresh batches too
        } else if (job.status === 'failed') {
          setLoading(false)
          setCurrentJob(null)
          setQueuePosition(null)
          alert('Generation failed: ' + (job.error || 'Unknown error'))
        } else if (job.status === 'cancelled') {
          setLoading(false)
          setCurrentJob(null)
          setQueuePosition(null)
          alert('Job was cancelled')
        } else {
          // Still running or queued, check again
          setTimeout(checkStatus, 2000)
        }
      } catch (error) {
        console.error('Error checking job status:', error)
        setLoading(false)
        setCurrentJob(null)
        setQueuePosition(null)
      }
    }

    checkStatus()
  }

  return (
    <PasswordGate>
      <div className="App">
        <header className="header">
          <div className="header-content">
            <div className="header-title">
              <h1>✨ Imagineer</h1>
              <p>AI Image Generation Toolkit</p>
            </div>
            <AuthButton />
          </div>
        </header>

        <div className="container">
          <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

          <div className="main-content">
            {activeTab === 'generate' && (
              <GenerateTab
                config={config}
                loading={loading}
                queuePosition={queuePosition}
                currentJob={currentJob}
                onGenerate={handleGenerate}
                onGenerateBatch={handleGenerateBatch}
              />
            )}

            {activeTab === 'gallery' && (
              <GalleryTab
                batches={batches}
                images={images}
                onRefreshImages={fetchImages}
                onRefreshBatches={fetchBatches}
              />
            )}

            {activeTab === 'albums' && (
              <AlbumsTab isAdmin={user?.role === 'admin'} />
            )}

            {activeTab === 'queue' && <QueueTab />}

            {activeTab === 'loras' && <LorasTab />}
          </div>
        </div>
      </div>
    </PasswordGate>
  )
}

export default App
