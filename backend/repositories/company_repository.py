from sqlalchemy import text
from backend.app.database.database import engine


def get_all_companies():
    """
    Fetch all companies from the companies table.
    """

    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT symbol, company_name, exchange
                FROM companies
                ORDER BY symbol
            """)
        )

        companies = result.fetchall()

    return companies