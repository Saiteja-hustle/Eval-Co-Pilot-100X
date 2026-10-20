-- Eval Co-Pilot: Stage 6 (login + RLS).
-- Run this once in the Supabase SQL Editor, AFTER schema.sql has already been run.
-- Old rows that still have user_id = null become invisible to everyone once RLS
-- turns on below -- that's expected and fine (see decisions.md known limits).

alter table questions alter column user_id set default auth.uid();
alter table runs alter column user_id set default auth.uid();
alter table answers alter column user_id set default auth.uid();

alter table questions enable row level security;
alter table runs enable row level security;
alter table answers enable row level security;

create policy "questions_select_own" on questions
  for select to authenticated
  using (auth.uid() = user_id);

create policy "questions_insert_own" on questions
  for insert to authenticated
  with check (auth.uid() = user_id);

create policy "questions_update_own" on questions
  for update to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "runs_select_own" on runs
  for select to authenticated
  using (auth.uid() = user_id);

create policy "runs_insert_own" on runs
  for insert to authenticated
  with check (auth.uid() = user_id);

create policy "runs_update_own" on runs
  for update to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "answers_select_own" on answers
  for select to authenticated
  using (auth.uid() = user_id);

create policy "answers_insert_own" on answers
  for insert to authenticated
  with check (auth.uid() = user_id);

create policy "answers_update_own" on answers
  for update to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
