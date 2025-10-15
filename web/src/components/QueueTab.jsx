import React, { useState, useEffect } from 'react'
import '../styles/QueueTab.css'

function QueueTab() {
  const [queueData, setQueueData] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    fetchQueueData()

    // Auto-refresh every 2 seconds if enabled
    if (autoRefresh) {
      const interval = setInterval(fetchQueueData, 2000)
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const fetchQueueData = async () => {
    try {
      const response = await fetch('/api/jobs')
      const data = await response.json()
      setQueueData(data)
    } catch (error) {
      console.error('Failed to fetch queue data:', error)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  const formatDuration = (startTime, endTime) => {
    if (!startTime || !endTime) return '-'
    const start = new Date(startTime)
    const end = new Date(endTime)
    const seconds = Math.floor((end - start) / 1000)
    return `${seconds}s`
  }

  const getStatusBadge = (status) => {
    const statusClass = `status-badge status-${status}`
    return <span className={statusClass}>{status}</span>
  }

  if (!queueData) {
    return <div className="queue-tab loading">Loading queue data...</div>
  }

  return (
    <div className="queue-tab">
      <div className="queue-header">
        <h2>Job Queue</h2>
        <div className="queue-controls">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
          <button onClick={fetchQueueData} className="refresh-button">
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Current Job */}
      <section className="queue-section">
        <h3>Currently Running</h3>
        {queueData.current ? (
          <div className="job-card current-job">
            <div className="job-header">
              <span className="job-id">Job #{queueData.current.id}</span>
              {getStatusBadge('running')}
            </div>
            <div className="job-details">
              <div className="job-field">
                <strong>Prompt:</strong>
                <span>{queueData.current.prompt}</span>
              </div>
              {queueData.current.lora_paths && queueData.current.lora_paths.length > 0 && (
                <div className="job-field">
                  <strong>LoRAs:</strong>
                  <span>{queueData.current.lora_paths.length} loaded</span>
                </div>
              )}
              <div className="job-field">
                <strong>Started:</strong>
                <span>{formatDate(queueData.current.started_at)}</span>
              </div>
              <div className="job-field">
                <strong>Settings:</strong>
                <span>
                  {queueData.current.width}×{queueData.current.height}, {queueData.current.steps} steps
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state">No job currently running</div>
        )}
      </section>

      {/* Queued Jobs */}
      <section className="queue-section">
        <h3>
          Queued Jobs
          {queueData.queue && queueData.queue.length > 0 && (
            <span className="count-badge">{queueData.queue.length}</span>
          )}
        </h3>
        {queueData.queue && queueData.queue.length > 0 ? (
          <div className="job-list">
            {queueData.queue.map((job, index) => (
              <div key={job.id} className="job-card queued-job">
                <div className="job-header">
                  <span className="job-id">
                    #{index + 1} - Job #{job.id}
                  </span>
                  {getStatusBadge('queued')}
                </div>
                <div className="job-details">
                  <div className="job-field">
                    <strong>Prompt:</strong>
                    <span>{job.prompt}</span>
                  </div>
                  {job.lora_paths && job.lora_paths.length > 0 && (
                    <div className="job-field">
                      <strong>LoRAs:</strong>
                      <span>{job.lora_paths.length} loaded</span>
                    </div>
                  )}
                  <div className="job-field">
                    <strong>Submitted:</strong>
                    <span>{formatDate(job.submitted_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">No jobs in queue</div>
        )}
      </section>

      {/* Job History */}
      <section className="queue-section">
        <h3>
          Recent History
          {queueData.history && queueData.history.length > 0 && (
            <span className="count-badge">{queueData.history.length}</span>
          )}
        </h3>
        {queueData.history && queueData.history.length > 0 ? (
          <div className="job-list history-list">
            {queueData.history.slice(0, 10).map((job) => (
              <div key={`${job.id}-${job.completed_at}`} className={`job-card history-job status-${job.status}`}>
                <div className="job-header">
                  <span className="job-id">Job #{job.id}</span>
                  {getStatusBadge(job.status)}
                  <span className="job-duration">
                    {formatDuration(job.started_at, job.completed_at)}
                  </span>
                </div>
                <div className="job-details">
                  <div className="job-field">
                    <strong>Prompt:</strong>
                    <span>{job.prompt}</span>
                  </div>
                  {job.output_path && job.status === 'completed' && (
                    <div className="job-field">
                      <strong>Output:</strong>
                      <span className="output-path">{job.output_path.split('/').pop()}</span>
                    </div>
                  )}
                  {job.error && (
                    <div className="job-field error">
                      <strong>Error:</strong>
                      <span>{job.error}</span>
                    </div>
                  )}
                  <div className="job-field">
                    <strong>Completed:</strong>
                    <span>{formatDate(job.completed_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">No completed jobs yet</div>
        )}
      </section>
    </div>
  )
}

export default QueueTab
