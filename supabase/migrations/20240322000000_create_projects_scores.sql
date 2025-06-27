-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    enterprise_name VARCHAR(255) NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending_review' CHECK (status IN ('pending_review', 'processing', 'completed', 'needs_info')),
    total_score DECIMAL(5,2),
    review_result VARCHAR(50) CHECK (review_result IN ('pass', 'fail', 'conditional')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create scores table (main dimensions)
CREATE TABLE IF NOT EXISTS scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    dimension VARCHAR(100) NOT NULL,
    score DECIMAL(5,2) NOT NULL,
    max_score DECIMAL(5,2) NOT NULL,
    comments TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, dimension)
);

-- Create score_details table (sub-dimensions)
CREATE TABLE IF NOT EXISTS score_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    score_id UUID NOT NULL REFERENCES scores(id) ON DELETE CASCADE,
    sub_dimension VARCHAR(100) NOT NULL,
    score DECIMAL(5,2) NOT NULL,
    max_score DECIMAL(5,2) NOT NULL,
    comments TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create missing_information table
CREATE TABLE IF NOT EXISTS missing_information (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    dimension VARCHAR(100) NOT NULL,
    information_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'provided', 'resolved')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_enterprise_name ON projects(enterprise_name);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scores_project_id ON scores(project_id);
CREATE INDEX IF NOT EXISTS idx_score_details_score_id ON score_details(score_id);
CREATE INDEX IF NOT EXISTS idx_missing_info_project_id ON missing_information(project_id);

-- Add RLS policies (Row Level Security)
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE score_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE missing_information ENABLE ROW LEVEL SECURITY;

-- Allow all operations for now (update with proper auth later)
CREATE POLICY "Allow all operations on projects" ON projects FOR ALL USING (true);
CREATE POLICY "Allow all operations on scores" ON scores FOR ALL USING (true);
CREATE POLICY "Allow all operations on score_details" ON score_details FOR ALL USING (true);
CREATE POLICY "Allow all operations on missing_information" ON missing_information FOR ALL USING (true);

-- Function to automatically update total_score when dimension scores change
CREATE OR REPLACE FUNCTION update_project_total_score()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE projects
    SET total_score = (
        SELECT COALESCE(SUM(score), 0)
        FROM scores
        WHERE project_id = COALESCE(NEW.project_id, OLD.project_id)
    ),
    updated_at = NOW()
    WHERE id = COALESCE(NEW.project_id, OLD.project_id);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update total_score
DROP TRIGGER IF EXISTS trigger_update_total_score_insert ON scores;
DROP TRIGGER IF EXISTS trigger_update_total_score_update ON scores;
DROP TRIGGER IF EXISTS trigger_update_total_score_delete ON scores;

CREATE TRIGGER trigger_update_total_score_insert
    AFTER INSERT ON scores
    FOR EACH ROW
    EXECUTE FUNCTION update_project_total_score();

CREATE TRIGGER trigger_update_total_score_update
    AFTER UPDATE ON scores
    FOR EACH ROW
    EXECUTE FUNCTION update_project_total_score();

CREATE TRIGGER trigger_update_total_score_delete
    AFTER DELETE ON scores
    FOR EACH ROW
    EXECUTE FUNCTION update_project_total_score();

-- Insert sample data for testing
INSERT INTO projects (id, enterprise_name, project_name, description, status, review_result) VALUES
    ('550e8400-e29b-41d4-a716-446655440001', '智云科技', 'AI智能客服', '基于大语言模型的智能客服系统', 'completed', 'pass'),
    ('550e8400-e29b-41d4-a716-446655440002', '慧医科技', '医疗影像分析', 'AI驱动的医疗影像诊断系统', 'needs_info', null),
    ('550e8400-e29b-41d4-a716-446655440003', '快运科技', '智能物流平台', '端到端物流管理解决方案', 'completed', 'pass'),
    ('550e8400-e29b-41d4-a716-446655440004', '绿源科技', '新能源监控', '智能电网监控系统', 'pending_review', null),
    ('550e8400-e29b-41d4-a716-446655440005', '数智科技', '数据分析平台', '企业级大数据分析平台', 'processing', null);

-- Insert sample scores
INSERT INTO scores (project_id, dimension, score, max_score, comments) VALUES
    ('550e8400-e29b-41d4-a716-446655440001', '团队能力', 26, 30, '团队成员具备丰富行业经验，结构合理'),
    ('550e8400-e29b-41d4-a716-446655440001', '产品&技术', 17, 20, '产品技术创新性强，已申请专利'),
    ('550e8400-e29b-41d4-a716-446655440001', '市场前景', 15, 20, '市场空间大，竞争格局良好'),
    ('550e8400-e29b-41d4-a716-446655440001', '商业模式', 16, 20, '盈利模式清晰，运营效率高'),
    ('550e8400-e29b-41d4-a716-446655440001', '财务情况', 8, 10, '财务状况良好，现金流健康'),

    ('550e8400-e29b-41d4-a716-446655440003', '团队能力', 28, 30, '团队经验丰富，执行力强'),
    ('550e8400-e29b-41d4-a716-446655440003', '产品&技术', 18, 20, '技术方案成熟，产品完成度高'),
    ('550e8400-e29b-41d4-a716-446655440003', '市场前景', 19, 20, '物流行业需求旺盛，市场前景广阔'),
    ('550e8400-e29b-41d4-a716-446655440003', '商业模式', 17, 20, '商业模式清晰，具有良好的扩展性'),
    ('550e8400-e29b-41d4-a716-446655440003', '财务情况', 8, 10, '财务规划合理，融资计划明确');

-- Insert sample missing information
INSERT INTO missing_information (project_id, dimension, information_type, description) VALUES
    ('550e8400-e29b-41d4-a716-446655440002', '财务情况', '财务报表', '缺少2023年财务报表'),
    ('550e8400-e29b-41d4-a716-446655440002', '团队能力', '团队经验', '需要补充核心团队过往项目经验'),
    ('550e8400-e29b-41d4-a716-446655440004', '市场前景', '市场调研', '缺少详细的市场调研数据'),
    ('550e8400-e29b-41d4-a716-446655440004', '商业模式', '盈利模式', '需要明确具体的盈利来源和模式');