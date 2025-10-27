import React, { useState, useEffect } from 'react';
import './TrainingTab.css';

const TrainingTab = () => {
  const [trainingRuns, setTrainingRuns] = useState([]);
  const [albums, setAlbums] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  // Form state for creating training runs
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    album_ids: [],
    config: {
      steps: 1000,
      rank: 4,
      learning_rate: 0.0001,
      batch_size: 1
    }
  });

  useEffect(() => {
    checkAdminStatus();
    fetchTrainingRuns();
    fetchAlbums();
  }, []);

  const checkAdminStatus = async () => {
    try {
      const response = await fetch('/api/auth/status');
      const data = await response.json();
      setIsAdmin(data.is_admin || false);
    } catch (err) {
      console.error('Error checking admin status:', err);
    }
  };

  const fetchTrainingRuns = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/training');
      const data = await response.json();
      setTrainingRuns(data.training_runs || []);
    } catch (err) {
      setError('Failed to fetch training runs');
      console.error('Error fetching training runs:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAlbums = async () => {
    try {
      const response = await fetch('/api/training/albums');
      const data = await response.json();
      setAlbums(data.albums || []);
    } catch (err) {
      console.error('Error fetching albums:', err);
    }
  };

  const handleCreateTraining = async (e) => {
    e.preventDefault();
    
    try {
      const response = await fetch('/api/training', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowCreateDialog(false);
        setFormData({
          name: '',
          description: '',
          album_ids: [],
          config: {
            steps: 1000,
            rank: 4,
            learning_rate: 0.0001,
            batch_size: 1
          }
        });
        fetchTrainingRuns();
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to create training run');
      }
    } catch (err) {
      setError('Failed to create training run');
      console.error('Error creating training run:', err);
    }
  };

  const handleStartTraining = async (runId) => {
    try {
      const response = await fetch(`/api/training/${runId}/start`, {
        method: 'POST',
      });

      if (response.ok) {
        fetchTrainingRuns();
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to start training');
      }
    } catch (err) {
      setError('Failed to start training');
      console.error('Error starting training:', err);
    }
  };

  const handleCancelTraining = async (runId) => {
    try {
      const response = await fetch(`/api/training/${runId}/cancel`, {
        method: 'POST',
      });

      if (response.ok) {
        fetchTrainingRuns();
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to cancel training');
      }
    } catch (err) {
      setError('Failed to cancel training');
      console.error('Error cancelling training:', err);
    }
  };

  const handleCleanupTraining = async (runId) => {
    try {
      const response = await fetch(`/api/training/${runId}/cleanup`, {
        method: 'POST',
      });

      if (response.ok) {
        fetchTrainingRuns();
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to cleanup training');
      }
    } catch (err) {
      setError('Failed to cleanup training');
      console.error('Error cleaning up training:', err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#4CAF50';
      case 'running': return '#2196F3';
      case 'failed': return '#F44336';
      case 'cancelled': return '#FF9800';
      case 'pending': return '#9E9E9E';
      case 'queued': return '#FFC107';
      default: return '#9E9E9E';
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="training-tab">
        <div className="loading">Loading training runs...</div>
      </div>
    );
  }

  return (
    <div className="training-tab">
      <div className="training-header">
        <h2>LoRA Training Pipeline</h2>
        {isAdmin && (
          <button 
            className="create-button"
            onClick={() => setShowCreateDialog(true)}
          >
            Create Training Run
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="training-runs">
        {trainingRuns.length === 0 ? (
          <div className="no-runs">
            <p>No training runs found. {isAdmin && 'Create your first training run to get started!'}</p>
          </div>
        ) : (
          trainingRuns.map((run) => (
            <div key={run.id} className="training-run-card">
              <div className="run-header">
                <h3>{run.name}</h3>
                <span 
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(run.status) }}
                >
                  {run.status.toUpperCase()}
                </span>
              </div>
              
              {run.description && (
                <p className="run-description">{run.description}</p>
              )}

              <div className="run-details">
                <div className="detail-item">
                  <strong>Progress:</strong> {run.progress}%
                </div>
                <div className="detail-item">
                  <strong>Created:</strong> {formatDate(run.created_at)}
                </div>
                {run.started_at && (
                  <div className="detail-item">
                    <strong>Started:</strong> {formatDate(run.started_at)}
                  </div>
                )}
                {run.completed_at && (
                  <div className="detail-item">
                    <strong>Completed:</strong> {formatDate(run.completed_at)}
                  </div>
                )}
                {run.final_checkpoint && (
                  <div className="detail-item">
                    <strong>Checkpoint:</strong> {run.final_checkpoint}
                  </div>
                )}
                {run.training_loss && (
                  <div className="detail-item">
                    <strong>Final Loss:</strong> {run.training_loss.toFixed(6)}
                  </div>
                )}
              </div>

              {run.status === 'running' && (
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${run.progress}%` }}
                  ></div>
                </div>
              )}

              {run.error_message && (
                <div className="error-details">
                  <strong>Error:</strong> {run.error_message}
                </div>
              )}

              {isAdmin && (
                <div className="run-actions">
                  {run.status === 'pending' && (
                    <button 
                      className="action-button start"
                      onClick={() => handleStartTraining(run.id)}
                    >
                      Start Training
                    </button>
                  )}
                  
                  {(run.status === 'pending' || run.status === 'queued' || run.status === 'running') && (
                    <button 
                      className="action-button cancel"
                      onClick={() => handleCancelTraining(run.id)}
                    >
                      Cancel
                    </button>
                  )}
                  
                  {(run.status === 'completed' || run.status === 'failed') && (
                    <button 
                      className="action-button cleanup"
                      onClick={() => handleCleanupTraining(run.id)}
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

      {/* Create Training Dialog */}
      {showCreateDialog && (
        <div className="dialog-overlay">
          <div className="dialog">
            <div className="dialog-header">
              <h3>Create Training Run</h3>
              <button 
                className="close-button"
                onClick={() => setShowCreateDialog(false)}
              >
                ×
              </button>
            </div>
            
            <form onSubmit={handleCreateTraining} className="training-form">
              <div className="form-group">
                <label htmlFor="name">Name *</label>
                <input
                  type="text"
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="description">Description</label>
                <textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                  rows="3"
                />
              </div>

              <div className="form-group">
                <label>Training Albums *</label>
                <div className="album-selection">
                  {albums.map((album) => (
                    <label key={album.id} className="album-checkbox">
                      <input
                        type="checkbox"
                        checked={formData.album_ids.includes(album.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              album_ids: [...formData.album_ids, album.id]
                            });
                          } else {
                            setFormData({
                              ...formData,
                              album_ids: formData.album_ids.filter(id => id !== album.id)
                            });
                          }
                        }}
                      />
                      <span>{album.name}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="steps">Training Steps</label>
                <input
                  type="number"
                  id="steps"
                  value={formData.config.steps}
                  onChange={(e) => setFormData({
                    ...formData,
                    config: {...formData.config, steps: parseInt(e.target.value)}
                  })}
                  min="100"
                  max="10000"
                />
              </div>

              <div className="form-group">
                <label htmlFor="rank">LoRA Rank</label>
                <input
                  type="number"
                  id="rank"
                  value={formData.config.rank}
                  onChange={(e) => setFormData({
                    ...formData,
                    config: {...formData.config, rank: parseInt(e.target.value)}
                  })}
                  min="1"
                  max="64"
                />
              </div>

              <div className="form-group">
                <label htmlFor="learning_rate">Learning Rate</label>
                <input
                  type="number"
                  id="learning_rate"
                  value={formData.config.learning_rate}
                  onChange={(e) => setFormData({
                    ...formData,
                    config: {...formData.config, learning_rate: parseFloat(e.target.value)}
                  })}
                  step="0.0001"
                  min="0.0001"
                  max="0.01"
                />
              </div>

              <div className="form-group">
                <label htmlFor="batch_size">Batch Size</label>
                <input
                  type="number"
                  id="batch_size"
                  value={formData.config.batch_size}
                  onChange={(e) => setFormData({
                    ...formData,
                    config: {...formData.config, batch_size: parseInt(e.target.value)}
                  })}
                  min="1"
                  max="8"
                />
              </div>

              <div className="form-actions">
                <button type="button" onClick={() => setShowCreateDialog(false)}>
                  Cancel
                </button>
                <button type="submit" disabled={formData.album_ids.length === 0}>
                  Create Training Run
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TrainingTab;