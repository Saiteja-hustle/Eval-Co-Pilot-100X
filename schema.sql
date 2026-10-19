-- Eval Co-Pilot: Stage 3 data model (PRD section 10).
-- Run this once in the Supabase SQL Editor (Project -> SQL Editor -> New query -> paste -> Run).
-- RLS is intentionally NOT enabled here (that's Stage 6).

create extension if not exists pgcrypto;

create table questions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  question_text text not null,
  good_answer_includes text,
  created_at timestamptz not null default now()
);

create table runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  created_at timestamptz not null default now(),
  app_address text not null,
  question_field_name text not null,
  answer_field_name text not null,
  global_wrong_text text
);

create table answers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  run_id uuid references runs(id),
  question_id uuid references questions(id),
  app_answer text,
  pass_fail text not null,
  fail_reason text,
  created_at timestamptz not null default now()
);
