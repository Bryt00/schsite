from django.db import migrations, models

def add_academic_year_column_if_not_exists(apps, schema_editor):
    table_name = "donations_wasscepayment"
    column_name = "academic_year"
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT count(*)
            FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
            """,
            [table_name, column_name]
        )
        exists = cursor.fetchone()[0] > 0
        if not exists:
            cursor.execute(
                f"""
                ALTER TABLE {table_name}
                ADD COLUMN {column_name} varchar(50) NOT NULL DEFAULT '2025/2026';
                """
            )

class Migration(migrations.Migration):

    dependencies = [
        ('donations', '0002_wassce_models'),
    ]

    operations = [
        migrations.RunPython(
            add_academic_year_column_if_not_exists,
            reverse_code=migrations.RunPython.noop
        ),
    ]

