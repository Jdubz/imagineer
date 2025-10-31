import React from 'react'
import { SkeletonBatchItem } from './Skeleton'
import type { BatchSummary } from '../types/models'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

interface BatchListProps {
  batches: BatchSummary[]
  onSelectBatch: (batchId: string) => void
  loading?: boolean
}

const BatchList: React.FC<BatchListProps> = ({ batches, onSelectBatch, loading = false }) => {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Generated Sets</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="batch-items">
            {Array.from({ length: 4 }).map((_, index) => (
              <SkeletonBatchItem key={index} />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!batches || batches.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Generated Sets</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="no-batches">No sets generated yet. Use "Generate Set" to create your first batch!</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generated Sets</CardTitle>
      </CardHeader>
      <CardContent>
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
      </CardContent>
    </Card>
  )
}

export default BatchList
