-- Migration: Add album_id to scrape_jobs table
-- Date: 2025-11-03
-- Description: Adds album_id foreign key to scrape_jobs to link successful scrapes to their created albums

-- Add album_id column (nullable since existing jobs won't have albums)
ALTER TABLE scrape_jobs
ADD COLUMN album_id INTEGER;

-- Add foreign key constraint to albums table
ALTER TABLE scrape_jobs
ADD CONSTRAINT fk_scrape_jobs_album_id
FOREIGN KEY (album_id) REFERENCES albums(id);

-- Create index for better query performance
CREATE INDEX idx_scrape_jobs_album_id ON scrape_jobs(album_id);
