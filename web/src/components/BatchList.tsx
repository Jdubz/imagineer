import React from 'react'
import { SkeletonBatchItem } from './Skeleton'
import type { BatchSummary } from '../types/models'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

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
          <div className="space-y-3">
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
          <p className="py-12 text-center text-sm text-muted-foreground">
            No sets generated yet. Use "Generate Set" to create your first batch!
          </p>
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
        <div className="space-y-3">
          {batches.map((batch) => (
            <button
              key={batch.batch_id}
              onClick={() => onSelectBatch(batch.batch_id)}
              className="w-full rounded-lg border border-border bg-card p-4 text-left transition-all hover:border-primary hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-3">
                  <h4 className="font-semibold text-foreground">{batch.name}</h4>
                  <Badge variant="secondary" className="shrink-0">
                    {batch.image_count} images
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">ID: {batch.batch_id}</p>
                <p className="text-xs text-muted-foreground">
                  Created: {batch.created ? new Date(batch.created).toLocaleString() : 'Unknown'}
                </p>
              </div>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export default BatchList
