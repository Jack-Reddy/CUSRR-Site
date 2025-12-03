import csv
from io import TextIOWrapper
from .models import User, db


def import_users_from_csv(file):
    '''
    Import users from a CSV file into the database.
    Expects columns: firstname, lastname, email, role (optional).
    :param file: File object representing the uploaded CSV file
    :return: Tuple (number of users added, list of warnings)
    '''
    warnings = []   # collect row-level issues

    duplicates = []
    bad_rows = []

    reader = csv.DictReader(
        TextIOWrapper(file, encoding='utf-8', errors='replace'))

    required = {"firstname", "lastname", "email"}
    fieldnames = reader.fieldnames or []
    missing = required - set(fieldnames)

    if missing:
        return 0, [f"Missing required CSV columns: {', '.join(missing)}"]

    added = 0
    row_num = 1

    for row in reader:
        row_num += 1

        if not row or all(v in ("", None) for v in row.values()):
            continue

        email = (row.get("email") or "").strip()
        if not email or "@" not in email:
            bad_rows.append(row_num)
            continue

        firstname = (row.get("firstname") or "").strip()
        lastname = (row.get("lastname") or "").strip()

        if not firstname or not lastname:
            bad_rows.append(row_num)
            continue

        if User.query.filter_by(email=email).first():
            duplicates.append(row_num)
            continue

        user = User(
            firstname=firstname,
            lastname=lastname,
            email=email,
            auth=row.get("role", "presenter")
        )

        db.session.add(user)
        added += 1

    if duplicates:
        warnings.append(
            f'''Duplicate emails found on rows: {', '.join(
                    map(
                        str,
                        duplicates))}. These rows were skipped.''')

    if bad_rows:
        warnings.append(
            f'''Invalid or missing data on rows: {', '.join(
                    map(
                        str,
                        bad_rows))}. These rows were skipped.''')
    db.session.commit()
    return added, warnings
