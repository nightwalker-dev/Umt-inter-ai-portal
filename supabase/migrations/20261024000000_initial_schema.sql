-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types
CREATE TYPE user_role AS ENUM ('admin', 'lead', 'user');
CREATE TYPE timetable_source AS ENUM ('manual', 'image');
CREATE TYPE timetable_status AS ENUM ('draft', 'active');
CREATE TYPE event_status AS ENUM ('upcoming', 'ongoing', 'completed');
CREATE TYPE task_status AS ENUM ('pending', 'completed', 'approved', 'rejected');

-- 1. teams
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    lead_id UUID, -- References profiles(id), added later
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. profiles
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role user_role NOT NULL,
    team_id UUID,
    is_active BOOLEAN NOT NULL DEFAULT true,
    must_change_password BOOLEAN NOT NULL DEFAULT true,
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Enforce team_id constraints: Users and Leads must have a team.
    CONSTRAINT user_lead_must_have_team CHECK (
        (role IN ('user', 'lead') AND team_id IS NOT NULL) OR
        (role = 'admin')
    )
);
ALTER TABLE profiles ADD CONSTRAINT fk_profiles_team FOREIGN KEY (team_id) REFERENCES teams(id);

-- Add lead_id foreign key to teams
ALTER TABLE teams ADD CONSTRAINT fk_teams_lead FOREIGN KEY (lead_id) REFERENCES profiles(id) ON DELETE SET NULL;

-- 3. timetables
CREATE TABLE timetables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    semester_label TEXT,
    source timetable_source NOT NULL,
    status timetable_status NOT NULL,
    valid_from DATE,
    valid_to DATE,
    image_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT one_active_timetable_per_user UNIQUE (user_id)
);

-- 4. timetable_slots
CREATE TABLE timetable_slots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timetable_id UUID NOT NULL REFERENCES timetables(id) ON DELETE CASCADE,
    day_of_week TEXT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    subject TEXT,
    room TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT start_before_end CHECK (start_time < end_time)
);

-- 5. events
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status event_status NOT NULL,
    created_by UUID NOT NULL REFERENCES profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT,
    assigned_to UUID NOT NULL REFERENCES profiles(id),
    assigned_by UUID NOT NULL REFERENCES profiles(id),
    team_id UUID NOT NULL REFERENCES teams(id),
    event_id UUID REFERENCES events(id),
    status task_status NOT NULL,
    priority TEXT,
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,
    review_note TEXT,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT review_note_required_if_rejected CHECK (
        (status = 'rejected' AND review_note IS NOT NULL AND trim(review_note) <> '') OR
        (status <> 'rejected')
    )
);

-- 7. task_status_history
CREATE TABLE task_status_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    from_status task_status,
    to_status task_status NOT NULL,
    changed_by UUID NOT NULL REFERENCES profiles(id),
    note TEXT,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. activity_log
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor_id UUID NOT NULL REFERENCES profiles(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Triggers for task constraints (TK-02)
CREATE OR REPLACE FUNCTION check_task_assignment()
RETURNS TRIGGER AS $$
DECLARE
    assigner_role user_role;
    assigner_team UUID;
    assignee_role user_role;
    assignee_team UUID;
BEGIN
    SELECT role, team_id INTO assigner_role, assigner_team FROM profiles WHERE id = NEW.assigned_by;
    SELECT role, team_id INTO assignee_role, assignee_team FROM profiles WHERE id = NEW.assigned_to;

    IF assigner_role = 'lead' THEN
        IF assignee_role != 'user' OR assignee_team != assigner_team OR NEW.assigned_to = NEW.assigned_by THEN
            RAISE EXCEPTION 'A Lead may assign only to Users of their own team.';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_task_assignment
BEFORE INSERT OR UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION check_task_assignment();

-- Storage bucket
INSERT INTO storage.buckets (id, name, public) VALUES ('timetables', 'timetables', false) ON CONFLICT DO NOTHING;

-- RLS Configuration
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE timetables ENABLE ROW LEVEL SECURITY;
ALTER TABLE timetable_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- Revoke anon access
REVOKE ALL ON teams FROM anon;
REVOKE ALL ON profiles FROM anon;
REVOKE ALL ON timetables FROM anon;
REVOKE ALL ON timetable_slots FROM anon;
REVOKE ALL ON events FROM anon;
REVOKE ALL ON tasks FROM anon;
REVOKE ALL ON task_status_history FROM anon;
REVOKE ALL ON activity_log FROM anon;

-- Helper functions for RLS
CREATE OR REPLACE FUNCTION get_auth_user_role() RETURNS user_role AS $$
BEGIN
  RETURN (SELECT role FROM profiles WHERE id = auth.uid() AND is_active = true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_auth_user_team() RETURNS UUID AS $$
BEGIN
  RETURN (SELECT team_id FROM profiles WHERE id = auth.uid() AND is_active = true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- SELECT Policies (No INSERT/UPDATE/DELETE per PRD rules for users)
CREATE POLICY profiles_select ON profiles FOR SELECT TO authenticated
USING (
    id = auth.uid()
    OR get_auth_user_role() = 'admin'
    OR (get_auth_user_role() = 'lead' AND team_id = get_auth_user_team())
);

CREATE POLICY teams_select ON teams FOR SELECT TO authenticated
USING (
    get_auth_user_role() = 'admin'
    OR id = get_auth_user_team()
);

CREATE POLICY timetables_select ON timetables FOR SELECT TO authenticated
USING (
    user_id = auth.uid()
    OR get_auth_user_role() = 'admin'
    OR (get_auth_user_role() = 'lead' AND user_id IN (SELECT id FROM profiles WHERE team_id = get_auth_user_team()))
);

CREATE POLICY timetable_slots_select ON timetable_slots FOR SELECT TO authenticated
USING (
    timetable_id IN (SELECT id FROM timetables WHERE
        user_id = auth.uid()
        OR get_auth_user_role() = 'admin'
        OR (get_auth_user_role() = 'lead' AND user_id IN (SELECT id FROM profiles WHERE team_id = get_auth_user_team()))
    )
);

CREATE POLICY events_select ON events FOR SELECT TO authenticated USING (true);

CREATE POLICY tasks_select ON tasks FOR SELECT TO authenticated
USING (
    assigned_to = auth.uid()
    OR get_auth_user_role() = 'admin'
    OR (get_auth_user_role() = 'lead' AND (team_id = get_auth_user_team() OR assigned_to = auth.uid()))
);

CREATE POLICY task_status_history_select ON task_status_history FOR SELECT TO authenticated
USING (
    task_id IN (SELECT id FROM tasks WHERE
        assigned_to = auth.uid()
        OR get_auth_user_role() = 'admin'
        OR (get_auth_user_role() = 'lead' AND (team_id = get_auth_user_team() OR assigned_to = auth.uid()))
    )
);

CREATE POLICY activity_log_select ON activity_log FOR SELECT TO authenticated USING (get_auth_user_role() = 'admin');

-- Append-only constraints via triggers (since we don't have DELETE/UPDATE policies, this acts as a defense-in-depth for the service role)
CREATE OR REPLACE FUNCTION prevent_modifications() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'This table is append-only.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_activity_log_modifications
BEFORE UPDATE OR DELETE ON activity_log
FOR EACH ROW EXECUTE FUNCTION prevent_modifications();

CREATE TRIGGER prevent_task_status_history_modifications
BEFORE UPDATE OR DELETE ON task_status_history
FOR EACH ROW EXECUTE FUNCTION prevent_modifications();

-- Seed data
INSERT INTO teams (name) VALUES ('Media'), ('Tech'), ('Operations') ON CONFLICT DO NOTHING;
