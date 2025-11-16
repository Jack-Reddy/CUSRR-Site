# services/csv_importer.py

import csv
from io import TextIOWrapper
from models import User, db

def import_users_from_csv(file):
    csv_data = TextIOWrapper(file, encoding='utf-8', errors='replace')
    reader = csv.DictReader(csv_data)

    required_columns = {"firstname", "lastname", "email"}
    fieldnames = reader.fieldnames or []
    missing = required_columns - set(fieldnames)

    if missing:
        return 0, f"Missing required CSV columns: {', '.join(missing)}"

    added = 0
    row_num = 1

    for row in reader:
        row_num += 1

        if not row or all(v in ("", None) for v in row.values()):
            continue

        email = (row.get("email") or "").strip()
        firstname = (row.get("firstname") or "").strip()
        lastname = (row.get("lastname") or "").strip()

        if not email or "@" not in email:
            continue
        if not firstname or not lastname:
            continue

        if User.query.filter_by(email=email).first():
            continue

        user = User(
            firstname=firstname,
            lastname=lastname,
            email=email,
            auth=row.get("role", "presenter")
        )

        db.session.add(user)
        added += 1

    db.session.commit()
    return added, None  # None = no error
