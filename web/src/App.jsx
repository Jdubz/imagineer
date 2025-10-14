import React, { useState, useEffect } from 'react'
import './styles/App.css'
import GenerateForm from './components/GenerateForm'
import ConfigDisplay from './components/ConfigDisplay'
import ImageGrid from './components/ImageGrid'
import BatchList from './components/BatchList'
import BatchGallery from './components/BatchGallery'

function App() {
  const [config, setConfig] = useState(null)
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(false)
  const [currentJob, setCurrentJob] = useState(null)
  const [queuePosition, setQueuePosition] = useState(null)

  // Batch state
  const [batches, setBatches] = useState([])
  const [selectedBatchId, setSelectedBatchId] = useState(null)
  const [viewMode, setViewMode] = useState('main') // 'main' or 'batch'

  // Load config on mount
  useEffect(() => {
    fetchConfig()
    fetchImages()
    fetchBatches()
  }, [])

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
        // Refresh batches list
        fetchBatches()
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

  const handleSelectBatch = (batchId) => {
    setSelectedBatchId(batchId)
    setViewMode('batch')
  }

  const handleBackToMain = () => {
    setViewMode('main')
    setSelectedBatchId(null)
    fetchBatches() // Refresh in case batch was updated
  }

  return (
    <div className="App">
      <header className="header">
        <h1>✨ Imagineer</h1>
        <p>AI Image Generation Toolkit</p>
      </header>

      <div className="container">
        <div className="main-content">
          {viewMode === 'main' ? (
            <>
              <GenerateForm
                onGenerate={handleGenerate}
                onGenerateBatch={handleGenerateBatch}
                loading={loading}
                config={config}
              />

              {loading && queuePosition !== null && (
                <div className="queue-status">
                  {queuePosition === 0 ? (
                    <p>🎨 Generating your image...</p>
                  ) : (
                    <p>⏳ Position in queue: {queuePosition}</p>
                  )}
                  {currentJob && (
                    <p className="job-prompt">Prompt: "{currentJob.prompt}"</p>
                  )}
                </div>
              )}

              {config && <ConfigDisplay config={config} />}

              <BatchList batches={batches} onSelectBatch={handleSelectBatch} />

              <ImageGrid images={images} onRefresh={fetchImages} />
            </>
          ) : (
            <BatchGallery batchId={selectedBatchId} onBack={handleBackToMain} />
          )}
        </div>
      </div>
    </div>
  )
}

export default App
