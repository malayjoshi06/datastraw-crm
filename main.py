from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import os

import models
import schemas
import database

app = FastAPI(title="Customer Ticket CRM API", version="1.0.0")

# Enable global CORS access rules
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enforce SQLite table generation on server startup execution
models.Base.metadata.create_all(bind=database.engine)

def generate_ticket_id(db: Session) -> str:
    count = db.query(models.Ticket).count()
    return f"TKT-{1001 + count}"


# --- CRUD API ENDPOINTS ---

@app.post("/api/tickets", response_model=schemas.TicketDetailResponse, status_code=201)
def create_ticket(ticket: schemas.TicketCreate, db: Session = Depends(database.get_db)):
    new_tkt_id = generate_ticket_id(db)
    db_ticket = models.Ticket(
        ticket_id=new_tkt_id,
        customer_name=ticket.customer_name,
        customer_email=ticket.customer_email,
        subject=ticket.subject,
        description=ticket.description,
        status="Open"
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


@app.get("/api/tickets", response_model=list[schemas.TicketListResponse])
def get_tickets(
    status: str = Query(None),
    search: str = Query(None),
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Ticket)
    if status:
        query = query.filter(models.Ticket.status == status)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (models.Ticket.ticket_id.ilike(search_filter)) |
            (models.Ticket.customer_name.ilike(search_filter)) |
            (models.Ticket.subject.ilike(search_filter)) |
            (models.Ticket.description.ilike(search_filter))
        )
    return query.order_by(models.Ticket.created_at.desc()).all()


@app.get("/api/tickets/{ticket_id}", response_model=schemas.TicketDetailResponse)
def get_ticket_detail(ticket_id: str, db: Session = Depends(database.get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket record not found.")
    return ticket


@app.put("/api/tickets/{ticket_id}", response_model=schemas.TicketDetailResponse)
def update_ticket(ticket_id: str, payload: schemas.TicketUpdate, db: Session = Depends(database.get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket record not found.")
    
    ticket.status = payload.status
    ticket.updated_at = datetime.now(timezone.utc)
    if payload.notes and payload.notes.strip():
        new_note = models.Note(ticket_id=ticket_id, note_text=payload.notes.strip())
        db.add(new_note)
        
    db.commit()
    db.refresh(ticket)
    return ticket


@app.get("/api/stats")
def get_dashboard_stats(db: Session = Depends(database.get_db)):
    total = db.query(models.Ticket).count()
    active = db.query(models.Ticket).filter(models.Ticket.status.in_(["Open", "In Progress"])).count()
    closed = db.query(models.Ticket).filter(models.Ticket.status == "Closed").count()
    return {"total": total, "active": active, "closed": closed}


# --- FRONTEND ROUTING PROVIDER ---
frontend_path = os.path.join(
    os.path.dirname(__file__),
    "frontend"
)

@app.get("/")
def serve_homepage():
    target_index = os.path.join(frontend_path, "index.html")
    if os.path.exists(target_index):
        return FileResponse(target_index)
    return {"error": "Frontend template index.html could not be located."}
