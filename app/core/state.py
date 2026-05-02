from typing import Annotated, TypedDict
import operator

class Finding(TypedDict):
    agent: str       
    severity: str     
    file: str         
    line: int         
    comment: str      

class AgentState(TypedDict):
    pr_number: int
    repo: str
    diff: str
    title: str
    description: str
    findings: Annotated[list[Finding], operator.add]
    next: str          
    agents_done: list 