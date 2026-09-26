from decimal import Decimal

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.diagnostic import DiagnosticCentre, DiagnosticTest
from app.models.user import User


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        admin = db.query(User).filter(User.email == "admin@evehealthcare.com").first()
        if not admin:
            admin = User(
                email="admin@evehealthcare.com",
                password_hash=hash_password("Admin@123"),
                full_name="EVE Admin",
                is_admin=True,
            )
            db.add(admin)

        user = db.query(User).filter(User.email == "user@evehealthcare.com").first()
        if not user:
            user = User(
                email="user@evehealthcare.com",
                password_hash=hash_password("User@123"),
                full_name="Demo User",
                is_admin=False,
            )
            db.add(user)

        # Centre 1: Noida
        centre1 = db.query(DiagnosticCentre).filter(
            DiagnosticCentre.name == "EVE Central Diagnostics - Noida"
        ).first()
        if not centre1:
            centre1 = DiagnosticCentre(
                name="EVE Central Diagnostics - Noida",
                location="Sector 62, Noida, Uttar Pradesh",
            )
            db.add(centre1)
            db.flush()

            db.add_all([
                DiagnosticTest(
                    centre_id=centre1.id,
                    name="Complete Blood Count (CBC)",
                    description="Measures red blood cells, white blood cells, hemoglobin, and platelets.",
                    price=Decimal("499.00"),
                ),
                DiagnosticTest(
                    centre_id=centre1.id,
                    name="Thyroid Profile Total (T3, T4, TSH)",
                    description="Evaluates thyroid gland function and metabolic health.",
                    price=Decimal("799.00"),
                ),
                DiagnosticTest(
                    centre_id=centre1.id,
                    name="Lipid Profile",
                    description="Measures good and bad cholesterol, and triglycerides.",
                    price=Decimal("650.00"),
                ),
            ])

        # Centre 2: Delhi
        centre2 = db.query(DiagnosticCentre).filter(
            DiagnosticCentre.name == "EVE Specialty Diagnostics - South Delhi"
        ).first()
        if not centre2:
            centre2 = DiagnosticCentre(
                name="EVE Specialty Diagnostics - South Delhi",
                location="Greater Kailash 1, New Delhi",
            )
            db.add(centre2)
            db.flush()

            db.add_all([
                DiagnosticTest(
                    centre_id=centre2.id,
                    name="Complete Blood Count (CBC)",
                    description="Automated full blood count analysis.",
                    price=Decimal("450.00"),
                ),
                DiagnosticTest(
                    centre_id=centre2.id,
                    name="HbA1c Glycated Hemoglobin",
                    description="3-month average blood glucose control marker.",
                    price=Decimal("550.00"),
                ),
                DiagnosticTest(
                    centre_id=centre2.id,
                    name="Vitamin D (25-OH)",
                    description="Assesses bone health and immunity markers.",
                    price=Decimal("1199.00"),
                ),
            ])

        db.commit()
        print("Seed complete successfully.")
        print("Default Credentials:")
        print("  Admin: admin@evehealthcare.com / Admin@123")
        print("  User:  user@evehealthcare.com / User@123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
