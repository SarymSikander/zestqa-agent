-- Users table (extends Supabase auth.users)
CREATE TABLE public.profiles (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  email TEXT NOT NULL,
  full_name TEXT,
  company TEXT,
  role TEXT DEFAULT 'user', -- 'user' or 'admin'
  hf_space_url TEXT,        -- their HuggingFace Space URL
  staging_url TEXT,         -- their product's staging portal URL
  production_url TEXT,      -- their product's production portal URL
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration for existing databases: run this in the Supabase SQL editor if
-- public.profiles was created before staging_url/production_url existed.
-- ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS staging_url TEXT;
-- ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS production_url TEXT;

-- User themes/appearance
CREATE TABLE public.themes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  sidebar_start TEXT DEFAULT '#151939',
  sidebar_end TEXT DEFAULT '#421b70',
  navbar_start TEXT DEFAULT '#151939',
  navbar_end TEXT DEFAULT '#421b70',
  hero_start TEXT DEFAULT '#7e56ef',
  hero_end TEXT DEFAULT '#463cb8',
  primary_color TEXT DEFAULT '#7e56ef',
  logo_base64 TEXT,
  project_name TEXT,        -- e.g. "Zambeel OMS"
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User integrations
CREATE TABLE public.integrations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  jira_connected BOOLEAN DEFAULT FALSE,
  github_connected BOOLEAN DEFAULT FALSE,
  slack_connected BOOLEAN DEFAULT FALSE,
  db_connected BOOLEAN DEFAULT FALSE,
  hf_configured BOOLEAN DEFAULT FALSE,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.themes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integrations ENABLE ROW LEVEL SECURITY;

-- Users can only read/write their own data
CREATE POLICY "Users can view own profile" ON public.profiles
  FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles
  FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "Users can view own theme" ON public.themes
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users can view own integrations" ON public.integrations
  FOR ALL USING (auth.uid() = user_id);

-- Admin check as a SECURITY DEFINER function: a policy on profiles that queries
-- profiles directly in its USING clause causes "infinite recursion detected in
-- policy" in Postgres, since evaluating the policy re-triggers itself. Wrapping
-- the check in a SECURITY DEFINER function runs that inner query with the
-- function owner's privileges, bypassing RLS for just that lookup.
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid() AND role = 'admin'
  );
$$ LANGUAGE sql SECURITY DEFINER STABLE SET search_path = public;

-- Admin can view all profiles (for admin panel)
CREATE POLICY "Admin can view all profiles" ON public.profiles
  FOR SELECT USING (public.is_admin());

-- Auto-provision profile/theme/integrations rows on signup. There's no INSERT
-- policy on these tables (by design — clients never create their own rows
-- directly), so this trigger is the only way a row gets created.
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name)
  VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'full_name');
  INSERT INTO public.themes (user_id) VALUES (NEW.id);
  INSERT INTO public.integrations (user_id) VALUES (NEW.id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
