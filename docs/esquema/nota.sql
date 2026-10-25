CREATE SEQUENCE nota_numero_seq;

CREATE TABLE nota (
  codigo text PRIMARY KEY,
  titulo text NOT NULL,
  contenido text NOT NULL,
  creada_en timestamptz NOT NULL,
  CONSTRAINT ck_nota_codigo_formato CHECK (codigo ~ '^NOTA-[0-9]{6}$'),
  CONSTRAINT ck_nota_titulo_largo CHECK (char_length(btrim(titulo)) BETWEEN 1 AND 120),
  CONSTRAINT ck_nota_contenido_largo CHECK (char_length(contenido) <= 10000)
);
