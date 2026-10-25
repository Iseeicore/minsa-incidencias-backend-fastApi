from sqlalchemy import Boolean, Column, MetaData, SmallInteger, Table, Text

metadata = MetaData()

categoria_incidencia_table = Table(
    "categoria_incidencia",
    metadata,
    Column("id", SmallInteger, primary_key=True),
    Column("codigo", Text, nullable=False),
    Column("plazo_dias_habiles", SmallInteger, nullable=False),
    Column("archiva_por_vencimiento", Boolean, nullable=False),
    Column("activo", Boolean, nullable=False),
    schema="catalogo",
)
