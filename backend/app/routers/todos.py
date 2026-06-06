from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agenda import Todo

router = APIRouter(prefix="/todos", tags=["todos"])


class TodoCreate(BaseModel):
    text: str


class TodoOut(BaseModel):
    id: int
    text: str
    done: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TodoOut])
async def list_todos(db: AsyncSession = Depends(get_db)) -> list[Todo]:
    result = await db.execute(select(Todo).order_by(Todo.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=TodoOut, status_code=201)
async def create_todo(body: TodoCreate, db: AsyncSession = Depends(get_db)) -> Todo:
    todo = Todo(text=body.text, done=False)
    db.add(todo)
    await db.flush()
    await db.refresh(todo)
    return todo


@router.patch("/{todo_id}", response_model=TodoOut)
async def toggle_todo(todo_id: int, db: AsyncSession = Depends(get_db)) -> Todo:
    result = await db.execute(select(Todo).where(Todo.id == todo_id))
    todo = result.scalar_one_or_none()
    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    todo.done = not todo.done
    await db.flush()
    await db.refresh(todo)
    return todo
