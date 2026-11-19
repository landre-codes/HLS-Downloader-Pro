"""Política de URLs e de rede compartilhada pelo scraper e pelo downloader.

O objetivo é ter uma única definição de:

* quais esquemas são aceitos (somente HTTP/HTTPS);
* quando um ``Referer`` pode ser enviado (nunca entre origens diferentes e
  nunca com query string, fragmento ou credenciais);
* quando um redirecionamento para um destino local/privado deve ser bloqueado.

A política é deliberadamente conservadora, mas não tenta ser um sandbox de
rede: o downloader ainda entrega a URL a processos externos (yt-dlp/ffmpeg).
Ela fecha o caminho automático de descoberta/redirect do scraper e impede que
segredos da URL original sejam encaminhados para outra origem.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import SplitResult, urlsplit, urlunsplit

HTTP_SCHEMES = frozenset({"http", "https"})
DEFAULT_PORTS = {"http": 80, "https": 443}
_LOCAL_NAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
    }
)


class UrlPolicyError(ValueError):
    """URL rejeitada pela política, com um motivo curto e estável."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _has_control_chars(value: str) -> bool:
    return any(ord(char) < 0x20 or char.isspace() for char in value)


def validate_http_url(url: str) -> SplitResult:
    """Valida uma URL de destino e devolve suas partes.

    Aceita apenas ``http``/``https`` com hostname não vazio e porta válida.
    Credenciais (userinfo) são permitidas no destino — alguns streams exigem
    autenticação — mas nunca são copiadas para o ``Referer``.
    """
    value = (url or "").strip()
    if not value:
        raise UrlPolicyError("empty_url")
    if _has_control_chars(value):
        raise UrlPolicyError("invalid_url")
    try:
        parts = urlsplit(value)
    except ValueError as exc:
        raise UrlPolicyError("invalid_url") from exc
    if parts.scheme.lower() not in HTTP_SCHEMES:
        raise UrlPolicyError("unsupported_scheme")
    try:
        hostname = parts.hostname
        _port = parts.port
    except ValueError as exc:
        raise UrlPolicyError("invalid_port") from exc
    if not hostname:
        raise UrlPolicyError("missing_host")
    if "\\" in parts.netloc or ("@" in parts.netloc and not parts.username):
        # Barras invertidas em autoridades confundem parsers; userinfo vazio é
        # tratado como URL malformada.
        raise UrlPolicyError("invalid_url")
    return parts


def effective_port(parts: SplitResult) -> int:
    try:
        port = parts.port
    except ValueError:
        port = None
    return port or DEFAULT_PORTS.get(parts.scheme.lower(), 0)


def same_origin(first: str, second: str) -> bool:
    """True quando esquema, host e porta efetiva coincidem."""
    try:
        left = validate_http_url(first)
        right = validate_http_url(second)
    except UrlPolicyError:
        return False
    return (
        left.scheme.lower() == right.scheme.lower()
        and (left.hostname or "").lower() == (right.hostname or "").lower()
        and effective_port(left) == effective_port(right)
    )


def _netloc_without_userinfo(parts: SplitResult) -> str:
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = effective_port(parts)
    default = DEFAULT_PORTS.get(parts.scheme.lower(), 0)
    if port and port != default:
        return f"{host}:{port}"
    return host


def sanitize_referer(page_url: str) -> str:
    """Transforma a página em um ``Referer`` sem segredos.

    Remove credenciais, query string e fragmento; mantém esquema, host, porta
    explícita e caminho. Retorna ``""`` para URLs inválidas.
    """
    try:
        parts = validate_http_url(page_url)
    except UrlPolicyError:
        return ""
    return urlunsplit(
        (
            parts.scheme.lower(),
            _netloc_without_userinfo(parts),
            parts.path or "/",
            "",
            "",
        )
    )


def referer_for(target_url: str, page_url: str | None) -> str:
    """``Referer`` permitido ao acessar ``target_url`` a partir da página.

    Só devolve valor quando o destino tem a mesma origem da página. Assim um
    CDN em outro host nunca recebe tokens presentes na URL original.
    """
    if not page_url or not same_origin(page_url, target_url):
        return ""
    return sanitize_referer(page_url)


def is_local_host(hostname: str | None) -> bool:
    """True para loopback, redes privadas, link-local e nomes locais óbvios."""
    host = (hostname or "").strip().strip("[]").rstrip(".").lower()
    if not host:
        return True
    if host in _LOCAL_NAMES or host.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def is_local_url(url: str) -> bool:
    """True quando o host da URL é literalmente local/privado."""
    try:
        parts = validate_http_url(url)
    except UrlPolicyError:
        return True
    return is_local_host(parts.hostname)


def resolves_to_local(hostname: str | None, port: int | None = None) -> bool:
    """Resolve o host e informa se algum endereço é local/privado.

    A resolução aqui reduz o risco de um host público apontar para a rede
    local, mas não elimina DNS rebinding/TOCTOU: a conexão HTTP resolve o nome
    novamente. O resultado deve ser tratado como defesa em profundidade, não
    como garantia absoluta.
    """
    host = (hostname or "").strip()
    if not host:
        return True
    try:
        infos = socket.getaddrinfo(host, port or 0, type=socket.SOCK_STREAM)
    except OSError:
        return False
    for info in infos:
        address = str(info[4][0])
        if is_local_host(address):
            return True
    return False


def redirect_allowed(
    original_url: str,
    target_url: str,
    *,
    allow_private: bool = False,
) -> tuple[bool, str]:
    """Valida um salto de redirecionamento.

    Destinos privados só são aceitos se o ponto de partida também for privado
    ou se a política permitir explicitamente (ex.: usuário baixando de um
    servidor na própria LAN). Uma página pública nunca redireciona o app para
    ``127.0.0.1``/``192.168.x.x``.
    """
    try:
        target = validate_http_url(target_url)
    except UrlPolicyError as exc:
        return False, exc.reason
    if allow_private:
        return True, "ok"
    original_local = is_local_url(original_url)
    target_local = is_local_host(target.hostname) or resolves_to_local(
        target.hostname, effective_port(target)
    )
    if target_local and not original_local:
        return False, "private_destination"
    return True, "ok"


__all__ = [
    "HTTP_SCHEMES",
    "UrlPolicyError",
    "effective_port",
    "is_local_host",
    "is_local_url",
    "redirect_allowed",
    "referer_for",
    "resolves_to_local",
    "same_origin",
    "sanitize_referer",
    "validate_http_url",
]
