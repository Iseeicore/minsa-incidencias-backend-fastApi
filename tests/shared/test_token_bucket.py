import pytest

from app.errors.limite_de_claves_invalido import LimiteDeClavesInvalido
from app.shared.token_bucket import BucketPolicy, TokenBucketLimiter, monotonic_ms

POLITICA = BucketPolicy(capacity=300, window_seconds=300)
MS = 1000


class Reloj:
    def __init__(self) -> None:
        self.ahora = 1_000_000.0

    def __call__(self) -> float:
        return self.ahora


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def limitador(reloj: Reloj) -> TokenBucketLimiter:
    return TokenBucketLimiter(reloj)


def _vaciar(limitador: TokenBucketLimiter, clave: str, politica: BucketPolicy, veces: int) -> None:
    for _ in range(veces):
        limitador.take(clave, politica)


def test_permite_una_rafaga_de_hasta_la_capacidad_y_luego_rechaza(limitador: TokenBucketLimiter) -> None:
    _vaciar(limitador, "a", POLITICA, 300)

    resultado = limitador.take("a", POLITICA)

    assert (resultado.allowed, resultado.remaining, resultado.limit) == (False, 0, 300)


def test_informa_los_tokens_restantes(limitador: TokenBucketLimiter) -> None:
    assert limitador.take("a", POLITICA).remaining == 299
    assert limitador.take("a", POLITICA).remaining == 298


def test_rellena_de_forma_continua(limitador: TokenBucketLimiter, reloj: Reloj) -> None:
    _vaciar(limitador, "a", POLITICA, 300)
    assert limitador.take("a", POLITICA).retry_after_seconds == 1

    reloj.ahora += 1 * MS
    assert limitador.take("a", POLITICA).allowed is True
    assert limitador.take("a", POLITICA).allowed is False

    reloj.ahora += 10 * MS
    _vaciar(limitador, "a", POLITICA, 10)
    assert limitador.take("a", POLITICA).allowed is False


def test_no_acumula_mas_que_la_capacidad_aunque_pase_mucho_tiempo(limitador: TokenBucketLimiter, reloj: Reloj) -> None:
    _vaciar(limitador, "a", POLITICA, 300)
    reloj.ahora += 24 * 60 * 60 * MS

    assert limitador.take("a", POLITICA).remaining == 299


def test_calcula_cuanto_esperar_cuando_el_relleno_es_lento(limitador: TokenBucketLimiter) -> None:
    lenta = BucketPolicy(capacity=5, window_seconds=900)
    _vaciar(limitador, "login", lenta, 5)

    assert limitador.take("login", lenta).retry_after_seconds == 180


def test_mantiene_cubetas_independientes_por_clave(limitador: TokenBucketLimiter) -> None:
    _vaciar(limitador, "a", POLITICA, 300)

    assert limitador.take("a", POLITICA).allowed is False
    assert limitador.take("b", POLITICA).allowed is True


def test_sweep_elimina_las_cubetas_llenas_y_conserva_las_activas(limitador: TokenBucketLimiter, reloj: Reloj) -> None:
    _vaciar(limitador, "activa", POLITICA, 300)
    limitador.take("ociosa", POLITICA)
    reloj.ahora += 2 * MS

    assert limitador.sweep() == 1
    assert limitador.size == 1

    reloj.ahora += 400 * MS
    assert limitador.sweep() == 1
    assert limitador.size == 0


def test_el_maximo_de_claves_es_estricto_y_vuelve_a_admitir_cuando_una_cubeta_expira(reloj: Reloj) -> None:
    limitado = TokenBucketLimiter(reloj, max_keys=2)
    assert limitado.take("a", POLITICA).allowed is True
    assert limitado.take("b", POLITICA).allowed is True

    saturado = limitado.take("c", POLITICA)
    assert (saturado.allowed, saturado.remaining, saturado.retry_after_seconds) == (False, 0, 1)
    assert limitado.size == 2

    reloj.ahora += 2 * MS
    assert limitado.take("c", POLITICA).allowed is True
    assert limitado.size == 1


def test_sin_cubetas_y_sin_espacio_el_reintento_es_de_un_segundo(reloj: Reloj) -> None:
    limitado = TokenBucketLimiter(reloj, max_keys=1)

    assert limitado._retry_after_saturation(reloj.ahora) == 1  # noqa: SLF001


@pytest.mark.parametrize("maximo", [0, -1])
def test_rechaza_un_maximo_de_claves_invalido(maximo: int, reloj: Reloj) -> None:
    with pytest.raises(LimiteDeClavesInvalido, match="max_keys debe ser un entero positivo"):
        TokenBucketLimiter(reloj, max_keys=maximo)


def test_el_error_de_limite_es_un_value_error() -> None:
    assert issubclass(LimiteDeClavesInvalido, ValueError)


def test_el_reloj_por_defecto_es_monotonico_en_milisegundos() -> None:
    primero = monotonic_ms()

    assert monotonic_ms() >= primero
