import argparse
import os
import sys
import uuid
import struct
import zipfile
import tarfile
import json
import hashlib
from pathlib import Path

from app.database import SessionLocal, Base, engine
from app.models import User, BackupSource, VerificationPolicy
from app.security import get_password_hash

def bootstrap_admin(email: str, password: str, role: str = "admin"):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User {email} already exists. Updating credentials.")
            user.password_hash = get_password_hash(password)
            user.role = role
        else:
            user = User(
                id=f"usr_{uuid.uuid4().hex[:12]}",
                email=email,
                password_hash=get_password_hash(password),
                role=role,
                is_active=True
            )
            db.add(user)
        db.commit()
        print(f"Administrator account '{email}' configured successfully with role '{role}'.")
    finally:
        db.close()

def create_synthetic_fixtures(dest_dir: str):
    dest_path = Path(dest_dir).resolve()
    dest_path.mkdir(parents=True, exist_ok=True)
    manifest = {}

    print(f"Generating synthetic backup test fixtures in {dest_path}...")

    # 1. Valid ZIP archive
    zip_path = dest_path / "valid_app_backup.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("app/config.json", json.dumps({"app": "demo", "env": "prod", "version": "1.0.0"}))
        zf.writestr("app/data.csv", "id,name,value\n1,Alpha,100\n2,Beta,200\n3,Gamma,300\n")
        zf.writestr("app/readme.txt", "Automated Backup Sentinel Verification Fixture\n")
    
    with open(zip_path, "rb") as f:
        manifest["valid_app_backup.zip"] = hashlib.sha256(f.read()).hexdigest()

    # 2. Corrupted ZIP archive
    bad_zip_path = dest_path / "corrupted_archive.zip"
    with open(bad_zip_path, "wb") as f:
        f.write(b"PK\x03\x04corrupted_header_data_not_valid_zip_payload_xxxx")
    with open(bad_zip_path, "rb") as f:
        manifest["corrupted_archive.zip"] = hashlib.sha256(f.read()).hexdigest()

    # 3. Path Traversal Attack ZIP (for security boundary testing)
    traversal_zip_path = dest_path / "traversal_attack.zip"
    with zipfile.ZipFile(traversal_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../../etc/passwd", "root:x:0:0:root:/root:/bin/bash\n")
        zf.writestr("normal.txt", "harmless file\n")
    with open(traversal_zip_path, "rb") as f:
        manifest["traversal_attack.zip"] = hashlib.sha256(f.read()).hexdigest()

    # 4. Valid TAR.GZ archive
    tar_path = dest_path / "valid_sys_backup.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        import io
        c1 = b"server_name: sentinel-node-1\nport: 8080\n"
        ti1 = tarfile.TarInfo("etc/server.conf")
        ti1.size = len(c1)
        tf.addfile(ti1, io.BytesIO(c1))

        c2 = b"log entries 2026-10-28 [INFO] System verified\n"
        ti2 = tarfile.TarInfo("var/log/system.log")
        ti2.size = len(c2)
        tf.addfile(ti2, io.BytesIO(c2))
    with open(tar_path, "rb") as f:
        manifest["valid_sys_backup.tar.gz"] = hashlib.sha256(f.read()).hexdigest()

    # 5. Valid PostgreSQL Custom Dump (PGDMP magic header)
    pg_path = dest_path / "valid_postgres.dump"
    with open(pg_path, "wb") as f:
        # Magic: PGDMP, v1.14.0, int=4, off=8, fmt=1 (custom), comp=1
        header = b"PGDMP" + struct.pack("BBB", 1, 14, 0) + struct.pack("BBBB", 4, 8, 1, 1)
        # Dummy TOC entry
        toc_sample = b"\x00\x00\x00\x01\x00\x00\x00\x00TABLE_USERS_DATA"
        f.write(header + toc_sample)
    with open(pg_path, "rb") as f:
        manifest["valid_postgres.dump"] = hashlib.sha256(f.read()).hexdigest()

    # 6. Valid SQL Dump
    sql_path = dest_path / "valid_database.sql"
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write("""-- Backup Sentinel PostgreSQL logical dump
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL
);

INSERT INTO users (username, email) VALUES
('alice', 'alice@example.com'),
('bob', 'bob@example.com'),
('sentinel', 'ops@sentinel.local');

COMMIT;
""")
    with open(sql_path, "rb") as f:
        manifest["valid_database.sql"] = hashlib.sha256(f.read()).hexdigest()

    # 7. Malformed SQL Dump
    bad_sql_path = dest_path / "malformed_database.sql"
    with open(bad_sql_path, "w", encoding="utf-8") as f:
        f.write("UNRECOGNIZED RANDOM STRING JUNK WITH NO DDL OR DML STATEMENTS")
    with open(bad_sql_path, "rb") as f:
        manifest["malformed_database.sql"] = hashlib.sha256(f.read()).hexdigest()

    # Save manifest
    manifest_file = dest_path / "checksum_manifest.json"
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)

    print("Synthetic fixtures created successfully:")
    for k, v in manifest.items():
        print(f"  - {k} (SHA256: {v[:16]}...)")

def seed_default_environment(fixtures_dir: str):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Admin user
        bootstrap_admin("admin@sentinel.local", "SentinelAdmin2026!")

        # 2. Local Source
        src_path = str(Path(fixtures_dir).resolve()).replace("\\", "/")
        source = db.query(BackupSource).filter(BackupSource.name == "Primary Local Backups").first()
        if not source:
            source = BackupSource(
                id=f"src_local_{uuid.uuid4().hex[:8]}",
                name="Primary Local Backups",
                description="Local storage directory containing daily production snapshots and archives.",
                source_type="local_fs",
                config={"root_path": src_path},
                enabled=True
            )
            db.add(source)
            db.commit()
            print(f"Created default backup source: {source.name} pointing to {src_path}")

        # 3. Default Policy
        policy = db.query(VerificationPolicy).filter(VerificationPolicy.name == "High Reliability Policy").first()
        if not policy:
            policy = VerificationPolicy(
                id=f"pol_default_{uuid.uuid4().hex[:8]}",
                name="High Reliability Policy",
                description="Comprehensive verification: daily cryptographic checksum, archive structural test, and isolated recovery test.",
                config={"checks": ["checksum", "structure", "recovery_test"]},
                rto_target_seconds=120,
                rpo_target_seconds=86400,
                schedule_cron="0 2 * * *",
                enabled=True
            )
            db.add(policy)
            db.commit()
            print("Created default verification policy: High Reliability Policy")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup Sentinel CLI Management")
    subparsers = parser.add_subparsers(dest="command")

    # Bootstrap admin
    admin_parser = subparsers.add_parser("bootstrap-admin")
    admin_parser.add_argument("--email", default="admin@sentinel.local")
    admin_parser.add_argument("--password", default="SentinelAdmin2026!")
    admin_parser.add_argument("--role", default="admin")

    # Fixtures
    fixture_parser = subparsers.add_parser("create-fixtures")
    fixture_parser.add_argument("--dir", default="./fixtures/synthetic-backups")

    # Seed
    seed_parser = subparsers.add_parser("seed")
    seed_parser.add_argument("--dir", default="./fixtures/synthetic-backups")

    args = parser.parse_args()
    if args.command == "bootstrap-admin":
        bootstrap_admin(args.email, args.password, args.role)
    elif args.command == "create-fixtures":
        create_synthetic_fixtures(args.dir)
    elif args.command == "seed":
        create_synthetic_fixtures(args.dir)
        seed_default_environment(args.dir)
    else:
        parser.print_help()
