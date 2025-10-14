import React from 'react'
import GenerateForm from './GenerateForm'
import ConfigDisplay from './ConfigDisplay'

function GenerateTab({
  config,
  loading,
  queuePosition,
  currentJob,
  onGenerate,
  onGenerateBatch
}) {
  return (
    <div className="generate-tab">
      <GenerateForm
        onGenerate={onGenerate}
        onGenerateBatch={onGenerateBatch}
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
    </div>
  )
}

export default GenerateTab
