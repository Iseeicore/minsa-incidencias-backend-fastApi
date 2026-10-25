import re

from app.nota.domain.constantes import DIGITOS_CODIGO, PREFIJO_CODIGO

PATRON_CODIGO = re.compile(rf"^{PREFIJO_CODIGO}[0-9]{{{DIGITOS_CODIGO}}}$")
