-- Create evaluations table
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_plan_id UUID NOT NULL REFERENCES business_plans(id),
    total_score DECIMAL(5,2) NOT NULL,
    evaluation_data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_evaluations_business_plan_id ON evaluations(business_plan_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_created_at ON evaluations(created_at);