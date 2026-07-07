"""
signer.py — Signature PAdES B-B optionnelle via pyHanko (US-128).

La signature est entièrement optionnelle :
  - Si pyHanko est absent → log warning, retourne PDF inchangé.
  - Si la config (cert P12 + password) est absente → log warning, retourne PDF inchangé.
  - Si une erreur survient → log error, retourne PDF inchangé (pas raise).

Variables d'environnement :
  BASSIRA_SIGNING_CERT_P12_PATH  : chemin vers le fichier .p12 / .pfx
  BASSIRA_SIGNING_CERT_PASSWORD  : mot de passe du cert (UTF-8)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("miroshark.signer")


# ─── Config ──────────────────────────────────────────────────────────────────


@dataclass
class SigningConfig:
    """Configuration de la signature PAdES.

    Attributes:
        cert_p12_path: Chemin absolu vers le fichier certificat .p12 / .pfx.
        cert_password: Mot de passe du certificat (UTF-8).
    """

    cert_p12_path: str
    cert_password: str

    @classmethod
    def from_env(cls) -> Optional["SigningConfig"]:
        """Construit une SigningConfig depuis les variables d'environnement.

        Retourne ``None`` si l'une ou l'autre des variables est absente/vide.
        """
        p12_path = os.getenv("BASSIRA_SIGNING_CERT_P12_PATH", "").strip()
        password = os.getenv("BASSIRA_SIGNING_CERT_PASSWORD", "").strip()
        if not p12_path or not password:
            return None
        return cls(cert_p12_path=p12_path, cert_password=password)


# ─── Exception ───────────────────────────────────────────────────────────────


class SigningError(Exception):
    """Levée uniquement pour les erreurs programmatiques internes."""


# ─── Helpers privés ──────────────────────────────────────────────────────────


def _pyhanko_available() -> bool:
    """True si pyHanko est importable."""
    try:
        import pyhanko  # noqa: F401
        return True
    except ImportError:
        return False


# ─── API publique ─────────────────────────────────────────────────────────────


def can_sign(config: Optional[SigningConfig] = None) -> bool:
    """Retourne True si la signature PAdES est possible.

    Conditions nécessaires :
      1. pyHanko est installé.
      2. La config (cert_p12_path + cert_password) est disponible.
      3. Le fichier .p12 existe sur le disque.
    """
    if not _pyhanko_available():
        return False
    cfg = config if config is not None else SigningConfig.from_env()
    if cfg is None:
        return False
    import os as _os
    return _os.path.isfile(cfg.cert_p12_path)


def sign_pdf_pades(
    pdf_bytes: bytes,
    *,
    config: Optional[SigningConfig] = None,
) -> bytes:
    """Signe le PDF en PAdES B-B (basic) via pyHanko.

    En cas d'absence de pyHanko, de config manquante ou d'erreur de
    signature, retourne ``pdf_bytes`` inchangé (avec un log warning/error).
    La signature est donc entièrement optionnelle — pas de raise.

    Args:
        pdf_bytes: Bytes du PDF à signer.
        config:    Config de signature. Si ``None``, lit les env vars.

    Returns:
        Bytes du PDF signé, ou ``pdf_bytes`` si la signature n'est pas
        disponible.
    """
    if not pdf_bytes:
        return pdf_bytes

    # 1. pyHanko disponible ?
    if not _pyhanko_available():
        logger.warning(
            "pyHanko non disponible — signature PAdES ignorée. "
            "Installer pyHanko>=0.20 pour activer la signature numérique."
        )
        return pdf_bytes

    # 2. Config disponible ?
    cfg = config if config is not None else SigningConfig.from_env()
    if cfg is None:
        logger.warning(
            "Config de signature absente (BASSIRA_SIGNING_CERT_P12_PATH / "
            "BASSIRA_SIGNING_CERT_PASSWORD non configurés) — PDF retourné sans signature."
        )
        return pdf_bytes

    # 3. Fichier cert présent ?
    if not os.path.isfile(cfg.cert_p12_path):
        logger.warning(
            "Fichier cert introuvable : %s — PDF retourné sans signature.",
            cfg.cert_p12_path,
        )
        return pdf_bytes

    # 4. Signature via pyHanko
    try:
        return _do_sign(pdf_bytes, cfg)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Erreur signature PAdES (%s: %s) — PDF retourné sans signature.",
            exc.__class__.__name__,
            exc,
        )
        return pdf_bytes


def _do_sign(pdf_bytes: bytes, cfg: SigningConfig) -> bytes:
    """Effectue la signature PAdES B-B via pyHanko.

    Raises:
        Exception: En cas d'erreur de signature (géré par l'appelant).
    """
    import io

    from pyhanko.sign import signers, fields as sign_fields
    from pyhanko.sign.signers.pdf_signer import PdfSignatureMetadata
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

    # Chargement du certificat P12
    with open(cfg.cert_p12_path, "rb") as f:
        p12_data = f.read()

    signer = signers.SimpleSigner.load_pkcs12(
        pfx_file=io.BytesIO(p12_data),
        passphrase=cfg.cert_password.encode("utf-8"),
    )

    # PDF writer incremental (requis par PAdES)
    input_buf = io.BytesIO(pdf_bytes)
    w = IncrementalPdfFileWriter(input_buf)

    # Métadonnées de signature PAdES B-B
    signature_meta = PdfSignatureMetadata(
        field_name="Signature",
        subfilter=sign_fields.SigSeedSubFilter.PADES,
    )

    output_buf = io.BytesIO()
    signers.sign_pdf(
        w,
        signature_meta=signature_meta,
        signer=signer,
        output=output_buf,
    )
    output_buf.seek(0)
    signed_bytes = output_buf.read()

    logger.info(
        "PDF signé PAdES B-B — taille originale=%d → signée=%d",
        len(pdf_bytes),
        len(signed_bytes),
    )

    return signed_bytes
