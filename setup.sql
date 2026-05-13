create table if not exists applications (
  id           uuid primary key default gen_random_uuid(),
  job_title    text not null,
  company      text,
  url          text unique not null,
  score        int,
  cover_letter text,
  status       text default 'pending',  -- pending | applied | rejected
  applied_at   timestamptz default now()
);

create index if not exists applications_status_idx on applications (status);
create index if not exists applications_score_idx on applications (score desc);
