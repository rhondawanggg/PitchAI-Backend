-- File: backend/supabase/migrations/20240323000000_create_review_history.sql

-- Create review_history table to track score changes
CREATE TABLE IF NOT EXISTS review_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    total_score DECIMAL(5,2) NOT NULL,
    dimensions JSONB NOT NULL, -- Store all dimension details as JSON
    modified_by VARCHAR(255) DEFAULT 'system', -- For now, default to system
    modification_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_review_history_project_id ON review_history(project_id);
CREATE INDEX IF NOT EXISTS idx_review_history_created_at ON review_history(created_at DESC);

-- Add RLS policy
ALTER TABLE review_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all operations on review_history" ON review_history FOR ALL USING (true);