"""GENERAR CREDENCIALES Y CERTIFICADO TLS PARA EL LABORATORIO LOCAL."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import secrets
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

root=Path(__file__).resolve().parent.parent
folder=root/'.secrets';folder.mkdir(exist_ok=True)
for name in ('agente_a_token','agente_b_token'):
    path=folder/name
    if not path.exists():path.write_text(secrets.token_hex(32),encoding='ascii')
keyfile=folder/'agente_tls.key';certfile=folder/'agente_tls.crt'
if keyfile.exists()!=certfile.exists():raise SystemExit('CERTIFICADO TLS INCOMPLETO')
if not keyfile.exists():
    key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'ingreso-agentes')])
    now=datetime.now(timezone.utc)
    cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=365))
          .add_extension(x509.SubjectAlternativeName([x509.DNSName('ingreso-agentes')]),critical=False)
          .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True).sign(key,hashes.SHA256()))
    keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
print('SECRETOS DE AGENTES Y TLS LOCAL PREPARADOS')
