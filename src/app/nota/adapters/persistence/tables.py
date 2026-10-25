from sqlalchemy import CheckConstraint, Column, DateTime, MetaData, Sequence, Table, Text

from app.nota.domain.constantes import CONTENIDO_MAX_LENGTH, TITULO_MAX_LENGTH
from app.nota.domain.patrones import PATRON_CODIGO

metadata = MetaData()

nota_numero_seq = Sequence("nota_numero_seq", metadata=metadata)

nota_table = Table(
    "nota",
    metadata,
    Column("codigo", Text, primary_key=True),
    Column("titulo", Text, nullable=False),
    Column("contenido", Text, nullable=False),
    Column("creada_en", DateTime(timezone=True), nullable=False),
    CheckConstraint(f"codigo ~ '{PATRON_CODIGO.pattern}'", name="ck_nota_codigo_formato"),
    CheckConstraint(f"char_length(btrim(titulo)) BETWEEN 1 AND {TITULO_MAX_LENGTH}", name="ck_nota_titulo_largo"),
    CheckConstraint(f"char_length(contenido) <= {CONTENIDO_MAX_LENGTH}", name="ck_nota_contenido_largo"),
)
