"""
Global Variables Service
Handles CRUD operations for global variables
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import models
import schemas
import logging
import re

logger = logging.getLogger(__name__)


class VariableService:
    """Service for managing global variables"""
    
    @staticmethod
    def create_variable(db: Session, variable: schemas.GlobalVariableCreate) -> models.GlobalVariable:
        """Create a new global variable"""
        # Validate variable name format (alphanumeric and underscores only)
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', variable.name):
            raise ValueError("Variable name must start with letter or underscore and contain only alphanumeric characters and underscores")
        
        # Check if variable already exists
        existing = db.query(models.GlobalVariable).filter(
            models.GlobalVariable.name == variable.name
        ).first()
        
        if existing:
            raise ValueError(f"Variable '{variable.name}' already exists")
        
        # Validate config based on variable type
        VariableService._validate_config(variable.variable_type, variable.config)
        
        db_variable = models.GlobalVariable(**variable.dict())
        db.add(db_variable)
        db.commit()
        db.refresh(db_variable)
        
        logger.info(f"Created global variable: {variable.name}")
        return db_variable
    
    @staticmethod
    def get_variable(db: Session, variable_id: int) -> Optional[models.GlobalVariable]:
        """Get a variable by ID"""
        return db.query(models.GlobalVariable).filter(
            models.GlobalVariable.id == variable_id
        ).first()
    
    @staticmethod
    def get_variable_by_name(db: Session, name: str) -> Optional[models.GlobalVariable]:
        """Get a variable by name"""
        return db.query(models.GlobalVariable).filter(
            models.GlobalVariable.name == name
        ).first()
    
    @staticmethod
    def get_all_variables(db: Session, active_only: bool = False) -> List[models.GlobalVariable]:
        """Get all variables"""
        query = db.query(models.GlobalVariable)
        
        if active_only:
            query = query.filter(models.GlobalVariable.is_active == True)
        
        return query.order_by(models.GlobalVariable.name).all()
    
    @staticmethod
    def update_variable(
        db: Session,
        variable_id: int,
        variable_update: schemas.GlobalVariableUpdate
    ) -> Optional[models.GlobalVariable]:
        """Update a variable"""
        db_variable = VariableService.get_variable(db, variable_id)
        
        if not db_variable:
            return None
        
        update_data = variable_update.dict(exclude_unset=True)
        
        # Validate name if changed
        if 'name' in update_data and update_data['name'] != db_variable.name:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', update_data['name']):
                raise ValueError("Variable name must start with letter or underscore and contain only alphanumeric characters and underscores")
            
            # Check if new name already exists
            existing = db.query(models.GlobalVariable).filter(
                models.GlobalVariable.name == update_data['name'],
                models.GlobalVariable.id != variable_id
            ).first()
            
            if existing:
                raise ValueError(f"Variable '{update_data['name']}' already exists")
        
        # Validate config if changed
        if 'config' in update_data and 'variable_type' in update_data:
            VariableService._validate_config(update_data['variable_type'], update_data['config'])
        elif 'config' in update_data:
            VariableService._validate_config(db_variable.variable_type, update_data['config'])
        
        for field, value in update_data.items():
            setattr(db_variable, field, value)
        
        db.commit()
        db.refresh(db_variable)
        
        logger.info(f"Updated global variable: {db_variable.name}")
        return db_variable
    
    @staticmethod
    def delete_variable(db: Session, variable_id: int) -> bool:
        """Delete a variable"""
        db_variable = VariableService.get_variable(db, variable_id)
        
        if not db_variable:
            return False
        
        db.delete(db_variable)
        db.commit()
        
        logger.info(f"Deleted global variable: {db_variable.name}")
        return True
    
    @staticmethod
    def _validate_config(variable_type: str, config: Dict[str, Any]):
        """Validate configuration based on variable type"""
        if variable_type == "static":
            if "value" not in config:
                raise ValueError("Static variable must have 'value' in config")
        
        elif variable_type == "db_query":
            required_fields = ["table", "column"]
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"DB query variable must have '{field}' in config")
        
        elif variable_type == "expression":
            if "expression" not in config:
                raise ValueError("Expression variable must have 'expression' in config")

