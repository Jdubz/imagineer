import React from 'react'
import type { BatchSummary } from '../types/models'

interface BatchListProps {
  batches: BatchSummary[]
  onSelectBatch: (batchId: string) => void
}

const BatchList: React.FC<BatchListProps> = ({ batches, onSelectBatch }) => {
  if (!batches || batches.length === 0) {
    return (
      <div className="batch-list">
        <h3>Generated Sets</h3>
        <p className="no-batches">No sets generated yet. Use "Generate Set" to create your first batch!</p>
      </div>
    )
  }

  return (
    <div className="batch-list">
      <h3>Generated Sets</h3>
      <div className="batch-items">
        {batches.map((batch) => (
          <div
            key={batch.batch_id}
            className="batch-item"
            onClick={() => onSelectBatch(batch.batch_id)}
          >
            <div className="batch-item-header">
              <h4>{batch.batch_id}</h4>
              <span className="batch-count">{batch.image_count} images</span>
            </div>
            <p className="batch-date">
              Created: {new Date(batch.created).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default BatchList
