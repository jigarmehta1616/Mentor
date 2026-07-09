-- Mentor schema. Applied automatically by docker-compose on first boot,
-- or via `python -m app.db.migrate` against DATABASE_URL.

CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  explain_level TEXT DEFAULT 'student',           -- 'eli5' | 'student' | 'expert'
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS concepts (
  id          TEXT PRIMARY KEY,
  topic       TEXT NOT NULL,
  name        TEXT NOT NULL,
  summary     TEXT,
  difficulty  INT DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_concepts_topic ON concepts (topic);

-- prerequisite edges: a DIRECTED ACYCLIC GRAPH (prereq -> concept)
CREATE TABLE IF NOT EXISTS concept_edges (
  concept_id  TEXT REFERENCES concepts(id),
  prereq_id   TEXT REFERENCES concepts(id),
  PRIMARY KEY (concept_id, prereq_id)
);

-- spaced-repetition mastery (SM-2 state), one row per (user, concept)
CREATE TABLE IF NOT EXISTS mastery (
  user_id         TEXT REFERENCES users(id),
  concept_id      TEXT REFERENCES concepts(id),
  easiness_factor REAL DEFAULT 2.5,               -- SM-2 EF
  interval_days   INT  DEFAULT 0,
  repetitions     INT  DEFAULT 0,
  next_review     TIMESTAMPTZ,                     -- when it's due again
  mastery_level   REAL DEFAULT 0.0,               -- 0..1
  last_score      INT,
  PRIMARY KEY (user_id, concept_id)
);
-- THE hot-path index: pull due items in O(log n + k), never a full scan.
CREATE INDEX IF NOT EXISTS idx_due ON mastery (user_id, next_review);

CREATE TABLE IF NOT EXISTS quiz_attempts (
  id            BIGSERIAL PRIMARY KEY,
  user_id       TEXT,
  concept_id    TEXT,
  question      TEXT,
  user_answer   TEXT,
  quality_score INT,                               -- 0..5 (feeds SM-2)
  misconception TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_attempts ON quiz_attempts (user_id, created_at);

-- session messages, but the AGENT only ever loads a bounded window + summary.
CREATE TABLE IF NOT EXISTS session_messages (
  id          BIGSERIAL PRIMARY KEY,
  session_id  TEXT,
  role        TEXT,
  content     TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_session ON session_messages (session_id, id);

-- one row per active learning session; holds the bounded agent state.
CREATE TABLE IF NOT EXISTS sessions (
  id               TEXT PRIMARY KEY,
  user_id          TEXT REFERENCES users(id),
  topic            TEXT NOT NULL,
  explain_level    TEXT DEFAULT 'student',
  path             JSONB DEFAULT '[]'::jsonb,       -- ordered concept ids
  current_concept  TEXT,
  running_summary  TEXT DEFAULT '',
  phase            TEXT DEFAULT 'teach',            -- teach | quiz | review
  state            JSONB DEFAULT '{}'::jsonb,       -- bounded AgentState snapshot
  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);
