from fastapi import APIRouter

from lib.crud import crud_router
from models.finance import (
    Bill, BillCreate, BillUpdate,
    Budget, BudgetCreate, BudgetUpdate,
    Expense, ExpenseCreate, ExpenseUpdate,
    Income, IncomeCreate, IncomeUpdate,
)

router = APIRouter()
router.include_router(crud_router(prefix="/incomes", collection="incomes", create_model=IncomeCreate, update_model=IncomeUpdate, out_model=Income, date_field="date"))
router.include_router(crud_router(prefix="/expenses", collection="expenses", create_model=ExpenseCreate, update_model=ExpenseUpdate, out_model=Expense, date_field="date"))
router.include_router(crud_router(prefix="/bills", collection="bills", create_model=BillCreate, update_model=BillUpdate, out_model=Bill, date_field="due_date", sort_desc=False, defaults={"status": "pending"}))
router.include_router(crud_router(prefix="/budgets", collection="budgets", create_model=BudgetCreate, update_model=BudgetUpdate, out_model=Budget, date_field="category", sort_desc=False))
