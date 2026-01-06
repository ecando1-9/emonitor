-- Script to create a PUBLIC bucket for hosting the Installer/EXE
-- This allows you to keep your Repo PRIVATE but share the App PUBLICLY.

-- 1. Create the bucket (if it doesn't exist)
INSERT INTO storage.buckets (id, name, public)
VALUES ('installers', 'installers', true)
ON CONFLICT (id) DO NOTHING;

-- 2. Allow PUBLIC access to READ (Download) files
-- Everyone (anon, authenticated) can download
CREATE POLICY "Public Select Installers"
ON storage.objects FOR SELECT
USING ( bucket_id = 'installers' );

-- 3. Allow Only ADMINs (service_role or authenticated with specific email) to UPLOAD/UPDATE
-- Modify this if you want to allow upload from the app (unlikely for installer)
-- Currently allowing authenticated users to upload for testing, or you can use the Dashboard.
CREATE POLICY "Authenticated Insert Installers"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK ( bucket_id = 'installers' );

CREATE POLICY "Authenticated Update Installers"
ON storage.objects FOR UPDATE
TO authenticated
USING ( bucket_id = 'installers' );

CREATE POLICY "Authenticated Delete Installers"
ON storage.objects FOR DELETE
TO authenticated
USING ( bucket_id = 'installers' );

-- NOTE: You can always upload files manually via the Supabase Dashboard -> Storage -> installers bucket.
