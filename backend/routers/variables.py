"""
Global Variables Router
API endpoints for managing global variables
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import schemas
from services.variable_service import VariableService

router = APIRouter(prefix="/api/variables", tags=["variables"])


@router.post("/", response_model=schemas.GlobalVariableResponse, status_code=201)
def create_variable(
    variable: schemas.GlobalVariableCreate,
    db: Session = Depends(get_db)
):
    """Create a new global variable"""
    try:
        return VariableService.create_variable(db, variable)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create variable: {str(e)}")


@router.get("/", response_model=List[schemas.GlobalVariableResponse])
def list_variables(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all global variables"""
    return VariableService.get_all_variables(db, active_only=active_only)


@router.get("/{variable_id}", response_model=schemas.GlobalVariableResponse)
def get_variable(
    variable_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific variable by ID"""
    variable = VariableService.get_variable(db, variable_id)
    if not variable:
        raise HTTPException(status_code=404, detail="Variable not found")
    return variable


@router.get("/name/{variable_name}", response_model=schemas.GlobalVariableResponse)
def get_variable_by_name(
    variable_name: str,
    db: Session = Depends(get_db)
):
    """Get a specific variable by name"""
    variable = VariableService.get_variable_by_name(db, variable_name)
    if not variable:
        raise HTTPException(status_code=404, detail="Variable not found")
    return variable


@router.put("/{variable_id}", response_model=schemas.GlobalVariableResponse)
def update_variable(
    variable_id: int,
    variable_update: schemas.GlobalVariableUpdate,
    db: Session = Depends(get_db)
):
    """Update a variable"""
    try:
        variable = VariableService.update_variable(db, variable_id, variable_update)
        if not variable:
            raise HTTPException(status_code=404, detail="Variable not found")
        return variable
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update variable: {str(e)}")


@router.delete("/{variable_id}", status_code=204)
def delete_variable(
    variable_id: int,
    db: Session = Depends(get_db)
):
    """Delete a variable"""
    success = VariableService.delete_variable(db, variable_id)
    if not success:
        raise HTTPException(status_code=404, detail="Variable not found")
    return None

