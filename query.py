from app import app, db
from models import Restaurant

def add_new_restaurant_fields():
    """
    Add new fields to the Restaurant model.
    This function should be called after updating the model and before running the app.
    """
    with app.app_context():
        # Check if the database needs migration
        inspector = db.inspect(db.engine)
        columns = [column['name'] for column in inspector.get_columns('restaurant')]
        
        # If is_suspended is not in the columns, we need to add all new columns
        if 'is_suspended' not in columns:
            print("Adding new columns to Restaurant table...")
            
            # Add is_suspended column
            db.engine.execute('ALTER TABLE restaurant ADD COLUMN is_suspended BOOLEAN DEFAULT FALSE;')
            
            # Add description column
            db.engine.execute('ALTER TABLE restaurant ADD COLUMN description TEXT;')
            
            # Add phone column
            db.engine.execute('ALTER TABLE restaurant ADD COLUMN phone VARCHAR(20);')
            
            # Add address column
            db.engine.execute('ALTER TABLE restaurant ADD COLUMN address TEXT;')
            
            # Add working_hours column
            db.engine.execute('ALTER TABLE restaurant ADD COLUMN working_hours VARCHAR(255);')
            
            # Add commission_rate column
            db.engine.execute('ALTER TABLE restaurant ADD COLUMN commission_rate FLOAT DEFAULT 10.0;')
            
            print("Migration completed successfully!")
        else:
            print("Restaurant table is already up to date.")

# Example of how to run this migration
if __name__ == "__main__":
    add_new_restaurant_fields()