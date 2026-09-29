from src.seed_data import seed_database

if __name__ == "__main__":
    print("Executing standalone seed script...")
    seed_database(force=True)
    print("Database seeding completed.")
