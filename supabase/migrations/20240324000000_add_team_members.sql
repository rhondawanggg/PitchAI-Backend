-- File: backend/supabase/migrations/20240324000000_add_team_members.sql

-- Add team_members field to projects table
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS team_members TEXT;

-- Set default team members for existing projects
UPDATE projects
SET team_members = '张三（CEO）、李四（CTO）、王五（COO）'
WHERE team_members IS NULL OR team_members = '';

-- Add comment for documentation
COMMENT ON COLUMN projects.team_members IS 'Team members information as text string';