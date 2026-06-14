create table if not exists pets (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  species text not null,
  created_at timestamptz default now()
);
