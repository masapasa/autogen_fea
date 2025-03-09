-- Users Table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Store securely hashed passwords!
    is_paid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Projects Table
CREATE TABLE projects (
    project_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tasks Table (Representing individual tasks within a project)
CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE,
    task_name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, completed, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_agent VARCHAR(255) -- Name of the primary agent responsible
);

-- Agent Definitions (Reusable agent configurations)
CREATE TABLE agent_definitions (
    agent_definition_id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    system_message TEXT, -- The core instruction for the agent
    capabilities TEXT[], -- Array of capabilities (e.g., ['FEA', 'CAD', 'Data Analysis'])
    llm_config JSONB -- Store LLM configuration as JSONB
);

-- Task Interactions (Logs of agent activity)
CREATE TABLE task_interactions (
    interaction_id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(task_id) ON DELETE CASCADE,
    agent_definition_id INTEGER REFERENCES agent_definitions(agent_definition_id),
    message TEXT, -- The message sent/received by the agent
    interaction_type VARCHAR(50), -- e.g., 'input', 'output', 'reasoning', 'error'
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB -- Store additional context (e.g., confidence scores, parameters)
);

-- Files (Associated with projects and tasks)
CREATE TABLE files (
    file_id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id) ON DELETE CASCADE,
    task_id INTEGER REFERENCES tasks(task_id), -- Can be NULL if associated with the whole project
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL, -- Path to storage (e.g., S3 bucket)
    file_type VARCHAR(50), -- e.g., 'CAD', 'FEA_RESULT', 'LOG'
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Feedback Table
CREATE TABLE feedback (
	feedback_id SERIAL PRIMARY KEY,
	user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
	task_id INTEGER REFERENCES tasks(task_id) ON DELETE CASCADE,
	feedback_text TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- Indexes for performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_task_interactions_task_id ON task_interactions(task_id);
CREATE INDEX idx_files_project_id ON files(project_id);
CREATE INDEX idx_files_task_id ON files(task_id);
CREATE INDEX idx_feedback_user_task ON feedback (user_id, task_id);

-- Create initial agent definitions.  These are templates.
INSERT INTO agent_definitions (agent_name, description, system_message, capabilities, llm_config) VALUES
('Engineer', 'Specialized in structural analysis and design.', 'You are an expert engineer...', ARRAY['FEA', 'CAD'], '{"model": "gpt-4o", "temperature": 0}'),
('Scientist', 'Focuses on data analysis and interpretation.', 'You are a data scientist...', ARRAY['Data Analysis', 'Statistics'], '{"model": "gpt-4o", "temperature": 0}'),
('Planner', 'Manages the overall workflow and coordinates agents.', 'You are a project planner...', ARRAY['Planning', 'Coordination'], '{"model": "gpt-4o", "temperature": 0}'),
('Critic', 'Evaluates the work of other agents and provides feedback.', 'You are a critical evaluator...', ARRAY['Review', 'Feedback'], '{"model": "gpt-4o", "temperature": 0}'),
('Executor', 'Executes code and interacts with external tools.', 'You are a code executor...', ARRAY['Code Execution', 'Tool Integration'], '{"model": "gpt-4o", "temperature": 0}');