-- Create business_plans table
CREATE TABLE IF NOT EXISTS business_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
    upload_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    error_message TEXT,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create index on project_id
CREATE INDEX IF NOT EXISTS idx_business_plans_project_id ON business_plans(project_id);

-- Create index on upload_time
CREATE INDEX IF NOT EXISTS idx_business_plans_upload_time ON business_plans(upload_time);

-- Create index on status for filtering
CREATE INDEX IF NOT EXISTS idx_business_plans_status ON business_plans(status);

-- Add RLS policies (simplified for demo - no user authentication yet)
ALTER TABLE business_plans ENABLE ROW LEVEL SECURITY;

-- Allow all operations for now (update with proper auth later)
CREATE POLICY "Allow all operations on business_plans"
    ON business_plans
    FOR ALL
    USING (true);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_business_plans_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_update_business_plans_updated_at ON business_plans;
CREATE TRIGGER trigger_update_business_plans_updated_at
    BEFORE UPDATE ON business_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_business_plans_updated_at();