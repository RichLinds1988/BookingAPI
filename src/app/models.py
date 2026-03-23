from datetime import datetime, timezone
from app import db
import bcrypt


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # index=True adds a database index on email for faster lookups during login
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)

    # Never store plain text passwords — only the bcrypt hash
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)

    # Role controls what the user can do — 'user' can book, 'admin' can manage resources
    # Default is 'user' so all new registrations are non-privileged
    role = db.Column(
        db.Enum('user', 'admin', name='user_role'), default='user', nullable=False
    )

    # lambda is used here so the datetime is evaluated at insert time, not at class definition time
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Defines the one-to-many relationship to Booking
    # backref="user" means you can access booking.user from a Booking instance
    # lazy=True means bookings are only loaded from the DB when you actually access them
    bookings = db.relationship("Booking", backref="user", lazy=True)

    def set_password(self, password: str):
        # bcrypt.gensalt() generates a random salt so the same password
        # produces a different hash each time — prevents rainbow table attacks
        # encode/decode converts between Python strings and bytes which bcrypt requires
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        # bcrypt handles the salt comparison internally — we just pass both values
        return bcrypt.checkpw(
            password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    def to_dict(self):
        # Only expose safe fields — never include password_hash in API responses
        return {"id": self.id, "email": self.email, "name": self.name, "role": self.role}


class Resource(db.Model):
    """A bookable resource — e.g. a room, desk, vehicle, or service slot."""

    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)  # Text allows longer strings than String(255)
    capacity = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)  # Soft delete — deactivate instead of deleting
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    bookings = db.relationship("Booking", backref="resource", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capacity": self.capacity,
            "is_active": self.is_active,
        }


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)

    # ForeignKey links this column to the primary key of another table
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey("resources.id"), nullable=False)

    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)

    # Number of guests for this booking — validated against the resource's capacity
    guests = db.Column(db.Integer, default=1, nullable=False)

    # Enum restricts the column to only these three values at the database level
    status = db.Column(
        db.Enum("confirmed", "cancelled", "pending", name="booking_status"), default="confirmed"
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Composite index on resource_id + start_time + end_time
    # This speeds up the conflict detection query which filters on all three columns
    # __table_args__ must be a tuple, hence the trailing comma
    __table_args__ = (
        db.Index("ix_bookings_resource_time", "resource_id", "start_time", "end_time"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "resource_id": self.resource_id,
            # Access the related resource's name via the backref defined in Resource
            "resource_name": self.resource.name if self.resource else None,
            # isoformat() converts datetime to a standard string like "2026-04-01T09:00:00"
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "notes": self.notes,
            "guests": self.guests,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
