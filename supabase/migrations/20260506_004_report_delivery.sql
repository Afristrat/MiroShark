-- Migration US-130 : livraison de rapports par URL signée TTL + tracking téléchargements
-- Created: 2026-05-05

-- ─── Table report_deliveries ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.report_deliveries (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id        text        NOT NULL,
    version          integer     NOT NULL,
    recipient_email  text        NOT NULL,
    recipient_name   text        NOT NULL DEFAULT '',
    signing_token    text        UNIQUE NOT NULL,
    expires_at       timestamptz NOT NULL,
    sent_at          timestamptz,
    sent_by          uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
    language         text        NOT NULL DEFAULT 'fr',
    email_status     text        NOT NULL DEFAULT 'pending',
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE  public.report_deliveries                  IS 'Livraisons de rapports par URL signée (US-130).';
COMMENT ON COLUMN public.report_deliveries.report_id        IS 'Identifiant du rapport (ex. report_abc123).';
COMMENT ON COLUMN public.report_deliveries.version          IS 'Version du snapshot livré.';
COMMENT ON COLUMN public.report_deliveries.signing_token    IS 'Token HMAC opaque — inclus dans le lien public /r/<token>.';
COMMENT ON COLUMN public.report_deliveries.expires_at       IS 'Date d''expiration du lien de téléchargement.';
COMMENT ON COLUMN public.report_deliveries.language         IS 'Langue de l''email envoyé : fr | en | ar.';
COMMENT ON COLUMN public.report_deliveries.email_status     IS 'Statut Resend : pending | sent | failed.';

-- Index pour les lookups fréquents
CREATE INDEX IF NOT EXISTS report_deliveries_report_id_idx   ON public.report_deliveries (report_id);
CREATE INDEX IF NOT EXISTS report_deliveries_expires_at_idx  ON public.report_deliveries (expires_at);
CREATE INDEX IF NOT EXISTS report_deliveries_email_idx       ON public.report_deliveries (recipient_email);

-- Trigger updated_at
CREATE OR REPLACE FUNCTION public.set_report_deliveries_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_report_deliveries_updated_at ON public.report_deliveries;
CREATE TRIGGER trg_report_deliveries_updated_at
    BEFORE UPDATE ON public.report_deliveries
    FOR EACH ROW EXECUTE FUNCTION public.set_report_deliveries_updated_at();

-- ─── Table report_downloads ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.report_downloads (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id     uuid        NOT NULL REFERENCES public.report_deliveries(id) ON DELETE CASCADE,
    downloaded_at   timestamptz NOT NULL DEFAULT now(),
    ip_address      inet,
    user_agent      text,
    country_code    text,
    referer         text
);

COMMENT ON TABLE  public.report_downloads              IS 'Tracking des téléchargements de rapports livrés (US-130).';
COMMENT ON COLUMN public.report_downloads.delivery_id  IS 'Référence vers la livraison (report_deliveries).';
COMMENT ON COLUMN public.report_downloads.country_code IS 'Code pays ISO 3166-1 alpha-2 (depuis CF-IPCountry).';

CREATE INDEX IF NOT EXISTS report_downloads_delivery_id_idx    ON public.report_downloads (delivery_id);
CREATE INDEX IF NOT EXISTS report_downloads_downloaded_at_idx  ON public.report_downloads (downloaded_at DESC);

-- ─── Row Level Security ───────────────────────────────────────────────────────

ALTER TABLE public.report_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_downloads  ENABLE ROW LEVEL SECURITY;

-- Super-admin Bassira : accès complet (via service_role bypass — les requêtes
-- backend utilisent le client admin qui bypass RLS, donc ces policies
-- couvrent les accès depuis un client Supabase authentifié côté front).

-- Policy : super-admin voit tout (lecture/écriture)
-- Le super-admin est identifié par son email (cf. BASSIRA_SUPER_ADMIN_EMAILS).
-- On stocke le flag is_super_admin dans les JWT claims via l'edge function auth.
-- En pratique les appels backend contournent RLS avec service_role ;
-- ces policies assurent la sécurité si un client JS accède directement.

CREATE POLICY "report_deliveries_super_admin_all"
    ON public.report_deliveries
    FOR ALL
    TO authenticated
    USING (
        -- Vérifie via la table org_members que l'utilisateur est super-admin
        -- ou appartient à l'org du rapport (via report_states.org_id)
        EXISTS (
            SELECT 1 FROM public.report_states rs
            WHERE rs.report_id = report_deliveries.report_id
              AND (
                  -- Super-admin : membre de l'org aimpower-bassira avec rôle owner/admin
                  EXISTS (
                      SELECT 1 FROM public.org_members om
                      JOIN public.organizations o ON o.id = om.org_id
                      WHERE om.user_id = auth.uid()
                        AND o.slug = 'aimpower-bassira'
                        AND om.role IN ('owner', 'admin')
                  )
                  OR
                  -- Org admin : membre de l'org du rapport
                  EXISTS (
                      SELECT 1 FROM public.org_members om
                      WHERE om.user_id = auth.uid()
                        AND om.org_id = rs.org_id
                        AND om.role IN ('owner', 'admin')
                  )
              )
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.report_states rs
            WHERE rs.report_id = report_deliveries.report_id
              AND (
                  EXISTS (
                      SELECT 1 FROM public.org_members om
                      JOIN public.organizations o ON o.id = om.org_id
                      WHERE om.user_id = auth.uid()
                        AND o.slug = 'aimpower-bassira'
                        AND om.role IN ('owner', 'admin')
                  )
                  OR
                  EXISTS (
                      SELECT 1 FROM public.org_members om
                      WHERE om.user_id = auth.uid()
                        AND om.org_id = rs.org_id
                        AND om.role IN ('owner', 'admin')
                  )
              )
        )
    );

CREATE POLICY "report_downloads_super_admin_all"
    ON public.report_downloads
    FOR ALL
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.report_deliveries rd
            JOIN public.report_states rs ON rs.report_id = rd.report_id
            WHERE rd.id = report_downloads.delivery_id
              AND (
                  EXISTS (
                      SELECT 1 FROM public.org_members om
                      JOIN public.organizations o ON o.id = om.org_id
                      WHERE om.user_id = auth.uid()
                        AND o.slug = 'aimpower-bassira'
                        AND om.role IN ('owner', 'admin')
                  )
                  OR
                  EXISTS (
                      SELECT 1 FROM public.org_members om
                      WHERE om.user_id = auth.uid()
                        AND om.org_id = rs.org_id
                        AND om.role IN ('owner', 'admin')
                  )
              )
        )
    )
    WITH CHECK (
        -- Les téléchargements sont insérés par le backend (service_role).
        -- En cas d'accès client direct, même condition que SELECT.
        EXISTS (
            SELECT 1 FROM public.report_deliveries rd
            JOIN public.report_states rs ON rs.report_id = rd.report_id
            WHERE rd.id = report_downloads.delivery_id
              AND (
                  EXISTS (
                      SELECT 1 FROM public.org_members om
                      JOIN public.organizations o ON o.id = om.org_id
                      WHERE om.user_id = auth.uid()
                        AND o.slug = 'aimpower-bassira'
                        AND om.role IN ('owner', 'admin')
                  )
                  OR
                  EXISTS (
                      SELECT 1 FROM public.org_members om
                      WHERE om.user_id = auth.uid()
                        AND om.org_id = rs.org_id
                        AND om.role IN ('owner', 'admin')
                  )
              )
        )
    );
