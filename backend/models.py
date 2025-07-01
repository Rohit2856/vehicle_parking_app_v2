import enum
from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey, DateTime, Float, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from werkzeug.security import generate_password_hash

Base = declarative_base()

# Enum for user roles
class UserRole(enum.Enum):
    admin = "admin"
    user = "user"

# Enum for parking spot status
class ParkingSpotStatus(enum.Enum):
    occupied = "O"
    available = "A"

# User model 
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    reservations = relationship('Reservation', back_populates='user')

# Parking Lot model
class ParkingLot(Base):
    __tablename__ = 'parking_lots'
    id = Column(Integer, primary_key=True)
    prime_location_name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    address = Column(String, nullable=True)
    pin_code = Column(String, nullable=True)
    number_of_spots = Column(Integer, nullable=False)
    spots = relationship('ParkingSpot', back_populates='lot', cascade='all, delete-orphan')

# Parking Spot model
class ParkingSpot(Base):
    __tablename__ = 'parking_spots'
    id = Column(Integer, primary_key=True)
    lot_id = Column(Integer, ForeignKey('parking_lots.id'), nullable=False)
    status = Column(Enum(ParkingSpotStatus), default=ParkingSpotStatus.available, nullable=False)
    lot = relationship('ParkingLot', back_populates='spots')
    reservations = relationship('Reservation', back_populates='spot')

# Reservation model
class Reservation(Base):
    __tablename__ = 'reservations'
    id = Column(Integer, primary_key=True)
    spot_id = Column(Integer, ForeignKey('parking_spots.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    parking_timestamp = Column(DateTime, nullable=False)
    leaving_timestamp = Column(DateTime, nullable=True)
    parking_cost = Column(Float, nullable=True)
    spot = relationship('ParkingSpot', back_populates='reservations')
    user = relationship('User', back_populates='reservations')

# Database creation script
def create_database():
    engine = create_engine('sqlite:///vehicle_parking_app.db', echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Predefined admin user
    admin_username = "admin"
    admin_password = "admin123" 
    admin_password_hash = generate_password_hash(admin_password)

    existing_admin = session.query(User).filter_by(username=admin_username, role=UserRole.admin).first()
    if not existing_admin:
        admin_user = User(
            username=admin_username,
            password_hash=admin_password_hash,
            role=UserRole.admin
        )
        session.add(admin_user)
        session.commit()

    session.close()

if __name__ == "__main__":
    create_database()
