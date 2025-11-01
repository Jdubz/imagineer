import React from 'react'
import GenerateForm from './GenerateForm'
import { useGeneration } from '../contexts/AppContext'

interface GenerateTabProps {
  isAdmin: boolean
}

const GenerateTab: React.FC<GenerateTabProps> = ({ isAdmin }) => {
  const { config, loading, queuePosition, handleGenerate } = useGeneration()
  return (
    <div className="generate-tab">
      {loading && (
        <div className="loading-indicator" role="status" aria-live="polite" aria-atomic="true">
          <div className="spinner"></div>
          <p>
            Generating image...
            {queuePosition !== null && queuePosition > 0 && (
              <span> (Queue position: {queuePosition})</span>
            )}
          </p>
        </div>
      )}

      {!loading && (
        <GenerateForm
          onGenerate={handleGenerate}
          loading={loading}
          config={config}
          isAdmin={isAdmin}
        />
      )}
    </div>
  )
}

export default GenerateTab
