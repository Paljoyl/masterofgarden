"""Trust only this project's public proxy CA before launching the game."""
import os
from pathlib import Path
import re
import ssl
import subprocess
import tempfile

from .environment import EnvironmentSetupError, FLAGS, owned_path


class CertificateSetupError(RuntimeError):
    pass


def proxy_profile(root):
    try:
        return owned_path(root, Path(root) / "runtime/proxy-profile")
    except EnvironmentSetupError as exc:
        raise CertificateSetupError(str(exc)) from None


def certificate_der(root):
    try:
        path = owned_path(root, proxy_profile(root) / "mitmproxy-ca-cert.pem")
        with path.open("rb") as source:
            value = source.read(128 * 1024 + 1)
        if len(value) > 128 * 1024:
            raise ValueError("Certificate too large")
        pem = value.decode("ascii")
        # Never import the combined CA/private-key file or unrelated PEM objects.
        if not re.fullmatch(r"\s*-----BEGIN CERTIFICATE-----\s*[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----\s*", pem):
            raise ValueError("Public certificate required")
        pem = pem.strip()
        ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT).load_verify_locations(cadata=pem)
        return ssl.PEM_cert_to_DER_cert(pem)
    except FileNotFoundError:
        raise CertificateSetupError("本项目接入工具尚未生成证书，请停止本次启动后重试；不要使用其他代理的证书。") from None
    except (OSError, ValueError, UnicodeError, EnvironmentSetupError):
        raise CertificateSetupError("本项目代理证书无法读取或格式不正确，请检查 runtime/proxy-profile 后重试。") from None


def certificate_trusted(der):
    try:
        return any(encoded == der and encoding == "x509_asn" and
                   (trust is True or ssl.Purpose.SERVER_AUTH.oid in trust)
                   for encoded, encoding, trust in ssl.enum_certificates("ROOT"))
    except (OSError, AttributeError):
        raise CertificateSetupError("无法检查 Windows 根证书信任，请使用当前 Windows 用户启动。") from None


def ensure_proxy_certificate(root, progress=lambda text: None):
    if os.name != "nt":
        raise CertificateSetupError("本地接入证书自动安装目前仅支持 Windows。")
    progress("正在检查本项目代理证书信任…")
    der = certificate_der(root)
    if certificate_trusted(der):
        progress("本项目代理证书已受信任，无需重复安装。")
        return
    progress("本项目代理证书未受信任，正在安装到当前用户的受信任根证书…")
    binary = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/certutil.exe"
    try:
        # Import a frozen, validated public certificate, not a mutable original/private key.
        with tempfile.TemporaryDirectory(prefix="mog-proxy-ca-") as directory:
            public = Path(directory) / "proxy-ca.cer"
            public.write_bytes(der)
            result = subprocess.run([str(binary), "-user", "-addstore", "Root", str(public)],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=60, creationflags=FLAGS)
        if result.returncode:
            raise CertificateSetupError("代理证书安装失败，游戏未启动。请检查当前用户的证书安装权限后重试。")
    except (OSError, subprocess.TimeoutExpired):
        raise CertificateSetupError("代理证书安装未完成，游戏未启动。请检查 Windows 证书权限或系统提示后重试。") from None
    if not certificate_trusted(der):
        raise CertificateSetupError("安装后未确认本项目证书受信任，游戏未启动。请检查 Windows 根证书策略后重试。")
    progress("本项目代理证书已安装并确认受信任。")
