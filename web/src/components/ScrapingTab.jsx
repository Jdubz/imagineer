import React, { useState, useEffect } from 'react';
import '../styles/ScrapingTab.css';

function ScrapingTab({ isAdmin }) {
  const [scrapeJobs, setScrapeJobs] = useState([]);
  const [showStartDialog, setShowStartDialog] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchJobs();
    fetchStats();

    // Auto-refresh every 5 seconds
    const interval = setInterval(() => {
      fetchJobs();
      fetchStats();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await fetch('/api/scraping/jobs');
      if (response.ok) {
        const data = await response.json();
        setScrapeJobs(data.jobs || []);
        setError(null);
      } else {
        setError('Failed to fetch scrape jobs');
      }
    } catch (err) {
      setError('Error fetching scrape jobs');
      console.error('Error fetching jobs:', err);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/scraping/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  const startScrape = async (url, name, description, depth, maxImages) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/scraping/start', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': 'Bearer admin_token' // This would be handled by auth system
        },
        credentials: 'include',
        body: JSON.stringify({ 
          url, 
          name, 
          description, 
          depth, 
          max_images: maxImages 
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Scrape job started:', data);
        fetchJobs();
        setShowStartDialog(false);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to start scrape job');
      }
    } catch (err) {
      setError('Error starting scrape job');
      console.error('Error starting scrape:', err);
    } finally {
      setLoading(false);
    }
  };

  const cancelJob = async (jobId) => {
    try {
      const response = await fetch(`/api/scraping/jobs/${jobId}/cancel`, {
        method: 'POST',
        headers: { 
          'Authorization': 'Bearer admin_token' // This would be handled by auth system
        },
        credentials: 'include'
      });

      if (response.ok) {
        fetchJobs();
      } else {
        setError('Failed to cancel job');
      }
    } catch (err) {
      setError('Error cancelling job');
      console.error('Error cancelling job:', err);
    }
  };

  const cleanupJob = async (jobId) => {
    try {
      const response = await fetch(`/api/scraping/jobs/${jobId}/cleanup`, {
        method: 'POST',
        headers: { 
          'Authorization': 'Bearer admin_token' // This would be handled by auth system
        },
        credentials: 'include'
      });

      if (response.ok) {
        fetchJobs();
      } else {
        setError('Failed to cleanup job');
      }
    } catch (err) {
      setError('Error cleaning up job');
      console.error('Error cleaning up job:', err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return '#f39c12';
      case 'running': return '#3498db';
      case 'completed': return '#27ae60';
      case 'failed': return '#e74c3c';
      case 'cancelled': return '#95a5a6';
      case 'cleaned_up': return '#7f8c8d';
      default: return '#95a5a6';
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="scraping-tab">
      <div className="scraping-header">
        <h2>Web Scraping</h2>
        {isAdmin && (
          <button 
            className="start-scrape-btn"
            onClick={() => setShowStartDialog(true)}
            disabled={loading}
          >
            {loading ? 'Starting...' : 'Start New Scrape'}
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {stats && (
        <div className="scraping-stats">
          <div className="stat-card">
            <h3>Total Jobs</h3>
            <span className="stat-number">{stats.total_jobs}</span>
          </div>
          <div className="stat-card">
            <h3>Images Scraped</h3>
            <span className="stat-number">{stats.total_images_scraped}</span>
          </div>
          <div className="stat-card">
            <h3>Recent Jobs (7 days)</h3>
            <span className="stat-number">{stats.recent_jobs}</span>
          </div>
        </div>
      )}

      <div className="scrape-jobs-list">
        {scrapeJobs.length === 0 ? (
          <div className="no-jobs">
            <p>No scrape jobs found. Start a new scrape to begin collecting training data.</p>
          </div>
        ) : (
          scrapeJobs.map(job => (
            <div key={job.id} className={`scrape-job-card status-${job.status}`}>
              <div className="job-header">
                <h3>{job.name}</h3>
                <span 
                  className="status-badge" 
                  style={{ backgroundColor: getStatusColor(job.status) }}
                >
                  {job.status}
                </span>
              </div>

              <div className="job-details">
                <div className="detail">
                  <strong>URL:</strong>
                  <a 
                    href={job.source_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="job-url"
                  >
                    {job.source_url}
                  </a>
                </div>

                {job.description && (
                  <div className="detail">
                    <strong>Description:</strong>
                    <span>{job.description}</span>
                  </div>
                )}

                {job.status === 'running' && (
                  <div className="progress-section">
                    <div className="progress-bar">
                      <div 
                        className="progress-fill" 
                        style={{ width: `${job.progress || 0}%` }}
                      ></div>
                    </div>
                    <div className="progress-text">
                      {job.progress || 0}% complete
                    </div>
                    {job.images_scraped > 0 && (
                      <div className="stats">
                        <span>Images scraped: {job.images_scraped}</span>
                      </div>
                    )}
                  </div>
                )}

                {job.status === 'completed' && (
                  <div className="completion-stats">
                    <div className="success-message">
                      ✓ Successfully scraped {job.images_scraped} images
                    </div>
                    {job.output_directory && (
                      <div className="output-info">
                        Output: {job.output_directory}
                      </div>
                    )}
                  </div>
                )}

                {job.status === 'failed' && job.error_message && (
                  <div className="error-details">
                    <strong>Error:</strong>
                    <span className="error-text">{job.error_message}</span>
                  </div>
                )}

                <div className="job-meta">
                  <div className="meta-item">
                    <strong>Created:</strong> {formatDate(job.created_at)}
                  </div>
                  {job.started_at && (
                    <div className="meta-item">
                      <strong>Started:</strong> {formatDate(job.started_at)}
                    </div>
                  )}
                  {job.completed_at && (
                    <div className="meta-item">
                      <strong>Completed:</strong> {formatDate(job.completed_at)}
                    </div>
                  )}
                </div>
              </div>

              {isAdmin && (
                <div className="job-actions">
                  {job.status === 'running' && (
                    <button 
                      className="cancel-btn"
                      onClick={() => cancelJob(job.id)}
                    >
                      Cancel
                    </button>
                  )}
                  {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && (
                    <button 
                      className="cleanup-btn"
                      onClick={() => cleanupJob(job.id)}
                    >
                      Cleanup
                    </button>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {showStartDialog && (
        <StartScrapeDialog
          onClose={() => setShowStartDialog(false)}
          onSubmit={startScrape}
          loading={loading}
        />
      )}
    </div>
  );
}

function StartScrapeDialog({ onClose, onSubmit, loading }) {
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [depth, setDepth] = useState(3);
  const [maxImages, setMaxImages] = useState(1000);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!url) return;
    
    const jobName = name || `Scrape ${url}`;
    const jobDescription = description || `Web scraping job for ${url}`;
    
    onSubmit(url, jobName, jobDescription, depth, maxImages);
  };

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={e => e.stopPropagation()}>
        <h2>Start Web Scrape</h2>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="url">URL to Scrape *</label>
            <input
              id="url"
              type="url"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://example.com/gallery"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="name">Job Name</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Auto-generated from URL"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Optional description for this scraping job"
              rows="3"
              disabled={loading}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="depth">Max Depth</label>
              <input
                id="depth"
                type="number"
                value={depth}
                onChange={e => setDepth(parseInt(e.target.value))}
                min="1"
                max="10"
                disabled={loading}
              />
              <small>How many links deep to follow (1-10)</small>
            </div>

            <div className="form-group">
              <label htmlFor="maxImages">Max Images</label>
              <input
                id="maxImages"
                type="number"
                value={maxImages}
                onChange={e => setMaxImages(parseInt(e.target.value))}
                min="1"
                max="10000"
                disabled={loading}
              />
              <small>Maximum images to download (1-10000)</small>
            </div>
          </div>

          <div className="dialog-actions">
            <button 
              type="submit" 
              className="submit-btn"
              disabled={loading || !url}
            >
              {loading ? 'Starting...' : 'Start Scrape'}
            </button>
            <button 
              type="button" 
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ScrapingTab;