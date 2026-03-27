
#################################################33
# backend/models.py

from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    query: str
    variant: Optional[str] = "r-mcts"       # MCTS variant for general queries
    simulations: Optional[int] = 5           # Number of MCTS simulations


class MailRequest(BaseModel):
    sender: str
    password: str
    recipient: str
    subject: str
    body: str
    attachment_path: Optional[str] = None