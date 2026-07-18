from fastapi import APIRouter

router = APIRouter()

@router.get("/companies")
def get_companies():
    return [
        {
            "symbol": "RELIANCE",
            "company_name": "Reliance Industries Limited",
            "exchange": "NSE"
        }
    ]