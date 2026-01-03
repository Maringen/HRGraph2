from pydantic import BaseModel
from typing import List, Optional

class Employee(BaseModel):
    name: str
    role: str
    skills: List[str]
    department: str

class Project(BaseModel):
    title: str
    status: str
    lead_employee: str