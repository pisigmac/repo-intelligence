CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS repos (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    branch TEXT NOT NULL DEFAULT 'main',
    commit_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    storage_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    repo TEXT NOT NULL,
    commit TEXT NOT NULL,
    entry_points JSONB DEFAULT '[]',
    interfaces JSONB DEFAULT '{}',
    dependencies TEXT[] DEFAULT '{}',
    signals JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS playbooks (
    id TEXT PRIMARY KEY,
    capability_id TEXT REFERENCES capabilities(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    steps JSONB NOT NULL DEFAULT '[]',
    validation JSONB DEFAULT '{}',
    rollback JSONB DEFAULT '{}',
    observability JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    playbook_id TEXT REFERENCES playbooks(id),
    status TEXT NOT NULL DEFAULT 'pending',
    steps_completed INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    logs JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_capabilities_repo ON capabilities(repo);
CREATE INDEX IF NOT EXISTS idx_capabilities_category ON capabilities(category);
CREATE INDEX IF NOT EXISTS idx_playbooks_capability ON playbooks(capability_id);
CREATE INDEX IF NOT EXISTS idx_executions_playbook ON executions(playbook_id);
