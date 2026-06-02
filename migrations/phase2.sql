-- Phase 2 Migration: Autonomous Intelligence & Self-Improvement Layer
-- Run this after Phase 1 init-db.sql

-- Execution telemetry additions
ALTER TABLE executions ADD COLUMN IF NOT EXISTS execution_time_ms INTEGER;
ALTER TABLE executions ADD COLUMN IF NOT EXISTS agent_trace JSONB DEFAULT '[]';
ALTER TABLE executions ADD COLUMN IF NOT EXISTS rollback_triggered BOOLEAN DEFAULT FALSE;

-- Feedback table
CREATE TABLE IF NOT EXISTS feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  execution_id UUID REFERENCES executions(id),
  playbook_id TEXT NOT NULL,
  status TEXT NOT NULL,
  execution_time_ms INTEGER,
  errors TEXT[] DEFAULT '{}',
  agent_actions JSONB DEFAULT '[]',
  context JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_playbook ON feedback(playbook_id);
CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);

-- Playbook versioning
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS version TEXT DEFAULT '1.0.0';
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS parent_id TEXT;
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS improved_from TEXT;
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS score NUMERIC(4,3) DEFAULT 0.0;
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS episodes INTEGER DEFAULT 0;
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'approved';

CREATE INDEX IF NOT EXISTS idx_playbooks_status ON playbooks(status);
CREATE INDEX IF NOT EXISTS idx_playbooks_score ON playbooks(score);

-- Approval workflow
CREATE TABLE IF NOT EXISTS approvals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  playbook_id TEXT NOT NULL,
  version TEXT NOT NULL,
  original_playbook_id TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  changes_summary JSONB,
  estimated_score_improvement NUMERIC(4,3),
  requested_by TEXT DEFAULT 'optimization-service',
  approved_by TEXT,
  reviewer_notes TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  decided_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
CREATE INDEX IF NOT EXISTS idx_approvals_playbook ON approvals(playbook_id);

-- Global knowledge store
CREATE TABLE IF NOT EXISTS global_knowledge (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  source_repo TEXT NOT NULL,
  source_playbook_id TEXT,
  playbook_template JSONB NOT NULL,
  applicable_tags TEXT[] DEFAULT '{}',
  language TEXT,
  framework TEXT,
  pattern_type TEXT,
  transfer_success_rate NUMERIC(4,3) DEFAULT 0.0,
  transfer_count INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_tags ON global_knowledge USING GIN(applicable_tags);
CREATE INDEX IF NOT EXISTS idx_knowledge_lang ON global_knowledge(language);
CREATE INDEX IF NOT EXISTS idx_knowledge_framework ON global_knowledge(framework);

-- RL scores history
CREATE TABLE IF NOT EXISTS rl_score_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  playbook_id TEXT NOT NULL,
  version TEXT NOT NULL,
  score NUMERIC(4,3) NOT NULL,
  success_rate NUMERIC(4,3),
  avg_execution_time_ms INTEGER,
  episodes INTEGER,
  computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_history_playbook ON rl_score_history(playbook_id);
CREATE INDEX IF NOT EXISTS idx_rl_history_computed ON rl_score_history(computed_at);

-- Cross-repo transfers log
CREATE TABLE IF NOT EXISTS transfers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  global_playbook_id TEXT REFERENCES global_knowledge(id),
  source_playbook_id TEXT,
  target_repo TEXT NOT NULL,
  new_playbook_id TEXT,
  status TEXT DEFAULT 'pending',
  adaptation_context JSONB DEFAULT '{}',
  validation_results JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_transfers_status ON transfers(status);
CREATE INDEX IF NOT EXISTS idx_transfers_target ON transfers(target_repo);
