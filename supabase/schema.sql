-- Tablas de FamousRelatives en Supabase.
-- Correr una vez en el editor SQL de Supabase (SQL Editor → New query → Run).
-- La extensión solo puede LEER estas tablas. Para editarlas usá el panel de
-- Supabase (Table Editor).

create table if not exists famosos (
  person_code text primary key,          -- ID de FamilySearch, ej. L7PK-SY2
  name        text not null,
  info        text not null default '',
  topics      text[] not null default '{}',  -- categorías, ej. {Deportistas,"Selección uruguaya"}
  paises      text[] not null default '{}',
  wiki        text                            -- link a Wikipedia (opcional)
);

create table if not exists categorias (
  nombre      text primary key,          -- igual al texto usado en famosos.topics
  descripcion text                       -- se muestra al elegir la categoría (admite HTML)
);

alter table famosos    enable row level security;
alter table categorias enable row level security;

drop policy if exists "lectura publica" on famosos;
drop policy if exists "lectura publica" on categorias;
create policy "lectura publica" on famosos    for select to anon using (true);
create policy "lectura publica" on categorias for select to anon using (true);
