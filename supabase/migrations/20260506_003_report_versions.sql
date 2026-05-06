-- Migration US-127 — Tables report_versions + report_comments
-- Versionning des rapports avec diff + annotations paragraph-level.

-- ─── report_versions ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS report_versions (
    version_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id         text        NOT NULL,
    version_number    int         NOT NULL,
    markdown_content  text        NOT NULL DEFAULT '',
    created_by        uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    comment           text,

    CONSTRAINT uq_report_version UNIQUE (report_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_report_versions_report_id
    ON report_versions(report_id);
CREATE INDEX IF NOT EXISTS idx_report_versions_created_at
    ON report_versions(created_at DESC);

-- ─── report_comments ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS report_comments (
    comment_id        uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id         text        NOT NULL,
    version_id        uuid        REFERENCES report_versions(version_id) ON DELETE SET NULL,
    paragraph_anchor  text        NOT NULL DEFAULT '',  -- sélecteur CSS ou hash du paragraphe
    author_id         uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
    body              text        NOT NULL DEFAULT '',
    resolved          bool        NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_report_comments_report_id
    ON report_comments(report_id);
CREATE INDEX IF NOT EXISTS idx_report_comments_resolved
    ON report_comments(report_id, resolved);

-- ─── RLS report_versions ──────────────────────────────────────────────────────

ALTER TABLE report_versions ENABLE ROW LEVEL SECURITY;

-- Super-admin : accès total (email dans BASSIRA_SUPER_ADMIN_EMAILS — géré côté backend)
-- Pour simplifier la RLS on accorde le service_role directement (toutes opérations)
-- et on bloque anon.

-- Politique : seul le service_role (bypass RLS) et les users authentifiés dont
-- l'org correspond à celle du rapport (via report_states) peuvent lire.
-- L'écriture est réservée au service_role (backend valide les autorisations).

CREATE POLICY "report_versions_service_role_all"
    ON report_versions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "report_versions_member_read"
    ON report_versions
    FOR SELECT
    TO authenticated
    USING (
        -- L'user appartient à l'org associée au rapport
        EXISTS (
            SELECT 1
            FROM report_states rs
            JOIN org_members om
              ON om.org_id = rs.org_id
             AND om.user_id = auth.uid()
            WHERE rs.report_id = report_versions.report_id
        )
    );

-- ─── RLS report_comments ──────────────────────────────────────────────────────

ALTER TABLE report_comments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "report_comments_service_role_all"
    ON report_comments
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "report_comments_member_read"
    ON report_comments
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM report_states rs
            JOIN org_members om
              ON om.org_id = rs.org_id
             AND om.user_id = auth.uid()
            WHERE rs.report_id = report_comments.report_id
        )
    );
