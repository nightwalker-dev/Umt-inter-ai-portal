-- 001_initial_schema.sql

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
    team_id UUID REFERENCES teams(id),
    is_active BOOLEAN NOT NULL DEFAULT true,
    must_change_password BOOLEAN NOT NULL DEFAULT true,
    created_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
    -- Enforce assigner rule on write: if assigned_by is lead, assigned_to must be in lead's team.
    -- We can't do complex cross-table checks easily in a simple CHECK constraint,
    -- so we will use a trigger for the assignee rule check.
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

-- RLS Configuration
-- Enable RLS on all tables
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE timetables ENABLE ROW LEVEL SECURITY;
ALTER TABLE timetable_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;

-- Disable anon access completely
-- Revoke all privileges from anon role on all tables
REVOKE ALL ON teams FROM anon;
REVOKE ALL ON profiles FROM anon;
REVOKE ALL ON timetables FROM anon;
REVOKE ALL ON timetable_slots FROM anon;
REVOKE ALL ON events FROM anon;
REVOKE ALL ON tasks FROM anon;
REVOKE ALL ON task_status_history FROM anon;
REVOKE ALL ON activity_log FROM anon;

-- Helper function to get current user role safely
CREATE OR REPLACE FUNCTION get_auth_user_role() RETURNS user_role AS $$
BEGIN
  RETURN (SELECT role FROM profiles WHERE id = auth.uid());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Helper function to get current user team safely
CREATE OR REPLACE FUNCTION get_auth_user_team() RETURNS UUID AS $$
BEGIN
  RETURN (SELECT team_id FROM profiles WHERE id = auth.uid());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- SELECT Policies
-- profiles: User own rows; Lead own team’s rows; Admin all rows
CREATE POLICY profiles_select ON profiles FOR SELECT TO authenticated
USING (
    id = auth.uid()
    OR get_auth_user_role() = 'admin'
    OR (get_auth_user_role() = 'lead' AND team_id = get_auth_user_team())
);

-- teams: Admin all; Lead own team; User own team
CREATE POLICY teams_select ON teams FOR SELECT TO authenticated
USING (
    get_auth_user_role() = 'admin'
    OR id = get_auth_user_team()
);

-- timetables: User own; Lead own team's; Admin all
CREATE POLICY timetables_select ON timetables FOR SELECT TO authenticated
USING (
    user_id = auth.uid()
    OR get_auth_user_role() = 'admin'
    OR (get_auth_user_role() = 'lead' AND user_id IN (SELECT id FROM profiles WHERE team_id = get_auth_user_team()))
);

-- timetable_slots: Same as timetables
CREATE POLICY timetable_slots_select ON timetable_slots FOR SELECT TO authenticated
USING (
    timetable_id IN (SELECT id FROM timetables WHERE
        user_id = auth.uid()
        OR get_auth_user_role() = 'admin'
        OR (get_auth_user_role() = 'lead' AND user_id IN (SELECT id FROM profiles WHERE team_id = get_auth_user_team()))
    )
);

-- events: Visible to all authenticated users
CREATE POLICY events_select ON events FOR SELECT TO authenticated
USING (true);

-- tasks: User sees own (assigned_to = auth.uid()); Lead sees team's and own; Admin sees all
CREATE POLICY tasks_select ON tasks FOR SELECT TO authenticated
USING (
    assigned_to = auth.uid()
    OR get_auth_user_role() = 'admin'
    OR (get_auth_user_role() = 'lead' AND (team_id = get_auth_user_team() OR assigned_to = auth.uid()))
);

-- task_status_history: Same logic as tasks
CREATE POLICY task_status_history_select ON task_status_history FOR SELECT TO authenticated
USING (
    task_id IN (SELECT id FROM tasks WHERE
        assigned_to = auth.uid()
        OR get_auth_user_role() = 'admin'
        OR (get_auth_user_role() = 'lead' AND (team_id = get_auth_user_team() OR assigned_to = auth.uid()))
    )
);

-- activity_log: Readable by Admins only
CREATE POLICY activity_log_select ON activity_log FOR SELECT TO authenticated
USING (get_auth_user_role() = 'admin');

-- Triggers for constraints
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

-- Fix team_id constraint and add is_active checks to RLS
ALTER TABLE profiles ALTER COLUMN team_id SET NOT NULL;

-- Redefine helper function to also check is_active
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

-- Drop NOT NULL constraint on team_id for admins
ALTER TABLE profiles ALTER COLUMN team_id DROP NOT NULL;
ALTER TABLE profiles ADD CONSTRAINT admin_no_team CHECK (role = 'admin' OR team_id IS NOT NULL);

-- Insert initial teams
INSERT INTO teams (name) VALUES ('Media'), ('Tech'), ('Operations') ON CONFLICT (name) DO NOTHING;
-- Create the private timetables storage bucket if it doesn't exist
INSERT INTO storage.buckets (id, name, public)
VALUES ('timetables', 'timetables', false)
ON CONFLICT (id) DO NOTHING;

-- Revoke all access from anon for the bucket
-- Since public is false, it's already private, but we can add an RLS policy just in case.
-- We won't add any policies since only the Service Role (FastAPI) will access this bucket.
-- RPC for creating a task with atomic history logging
CREATE OR REPLACE FUNCTION create_task_with_history(
    p_title TEXT,
    p_description TEXT,
    p_assigned_to UUID,
    p_assigned_by UUID,
    p_team_id UUID,
    p_event_id UUID,
    p_priority TEXT,
    p_due_date TIMESTAMPTZ
) RETURNS UUID AS $$
DECLARE
    v_task_id UUID;
BEGIN
    INSERT INTO tasks (title, description, assigned_to, assigned_by, team_id, event_id, status, priority, due_date)
    VALUES (p_title, p_description, p_assigned_to, p_assigned_by, p_team_id, p_event_id, 'pending', p_priority, p_due_date)
    RETURNING id INTO v_task_id;

    INSERT INTO task_status_history (task_id, to_status, changed_by, note)
    VALUES (v_task_id, 'pending', p_assigned_by, 'Task created');

    INSERT INTO activity_log (actor_id, action, entity_type, entity_id, details)
    VALUES (p_assigned_by, 'task_created', 'task', v_task_id, jsonb_build_object('title', p_title, 'assigned_to', p_assigned_to));

    RETURN v_task_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC for transitioning a task with atomic history logging
CREATE OR REPLACE FUNCTION transition_task_with_history(
    p_task_id UUID,
    p_from_status task_status,
    p_to_status task_status,
    p_changed_by UUID,
    p_note TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_updated BOOLEAN;
BEGIN
    -- Update the task, ensuring from_status matches
    UPDATE tasks
    SET status = p_to_status,
        updated_at = NOW(),
        completed_at = CASE WHEN p_to_status = 'completed' THEN NOW() ELSE completed_at END,
        reviewed_by = CASE WHEN p_to_status IN ('approved', 'rejected') THEN p_changed_by ELSE reviewed_by END,
        reviewed_at = CASE WHEN p_to_status IN ('approved', 'rejected') THEN NOW() ELSE reviewed_at END,
        review_note = CASE WHEN p_to_status IN ('approved', 'rejected') THEN p_note ELSE review_note END
    WHERE id = p_task_id AND status = p_from_status;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    INSERT INTO task_status_history (task_id, from_status, to_status, changed_by, note)
    VALUES (p_task_id, p_from_status, p_to_status, p_changed_by, p_note);

    INSERT INTO activity_log (actor_id, action, entity_type, entity_id)
    VALUES (p_changed_by, 'task_marked_' || p_to_status::text, 'task', p_task_id);

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
