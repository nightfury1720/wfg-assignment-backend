from transactions.database import engine, test_connection, Base
from transactions.sqlalchemy_models import Transaction

if __name__ == "__main__":
    print("Testing database connection...")
    if test_connection():
        print("\nCreating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
    else:
        print("Failed to connect to database. Please check your .env file.")

