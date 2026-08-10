import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

GHOST_ID = "hosp_default"

async def main():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        q = "SELECT id, name FROM hospitals WHERE id = :hid"
        r = await conn.execute(text(q), {"hid": GHOST_ID})
        row = r.fetchone()
        if not row:
            print("hosp_default NOT FOUND - already clean")
            return
        print("Found ghost hospital:", row[0], row[1])

        stmts = [
            "DELETE ash FROM appointment_status_history ash INNER JOIN appointments a ON ash.appointment_id = a.id WHERE a.hospital_id = :hid",
            "DELETE pi FROM patient_intakes pi INNER JOIN appointments a ON pi.appointment_id = a.id WHERE a.hospital_id = :hid",
            "DELETE FROM appointments WHERE hospital_id = :hid",
            "DELETE ds FROM doctor_specializations ds INNER JOIN doctors d ON ds.doctor_id = d.id WHERE d.hospital_id = :hid",
            "DELETE dsc FROM doctor_schedules dsc INNER JOIN doctors d ON dsc.doctor_id = d.id WHERE d.hospital_id = :hid",
            "DELETE dl FROM doctor_leaves dl INNER JOIN doctors d ON dl.doctor_id = d.id WHERE d.hospital_id = :hid",
            "DELETE ur FROM user_roles ur INNER JOIN users u ON ur.user_id = u.id WHERE u.hospital_id = :hid",
            "DELETE FROM users WHERE hospital_id = :hid",
            "DELETE FROM doctors WHERE hospital_id = :hid",
            "DELETE FROM patients WHERE hospital_id = :hid",
            "DELETE FROM hospital_holidays WHERE hospital_id = :hid",
            "DELETE FROM working_hours WHERE hospital_id = :hid",
            "DELETE FROM departments WHERE hospital_id = :hid",
            "DELETE FROM hospital_settings WHERE hospital_id = :hid",
            "DELETE FROM call_logs WHERE hospital_id = :hid",
            "DELETE FROM hospitals WHERE id = :hid",
        ]
        for stmt in stmts:
            try:
                result = await conn.execute(text(stmt), {"hid": GHOST_ID})
                print(f"OK ({result.rowcount} rows): {stmt[:60]}...")
            except Exception as e:
                print(f"SKIP: {str(e)[:100]}")

        print("\nDONE - hosp_default removed")
        r2 = await conn.execute(text("SELECT id, name FROM hospitals"))
        print("Remaining hospitals:")
        for row in r2.fetchall():
            print(f"  id={row[0]}, name={row[1]}")
    await engine.dispose()

asyncio.run(main())
