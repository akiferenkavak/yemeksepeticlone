from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    address = db.Column(db.Text, nullable=True)
    user_type = db.Column(db.String(20), nullable=False)  # 'admin', 'restaurant', 'user', 'delivery'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    reset_code = db.Column(db.String(100), nullable=True)
    reset_code_expiry = db.Column(db.DateTime, nullable=True)
    
    # Relationship with Restaurant for restaurant owners
    restaurant = db.relationship('Restaurant', backref='owner', uselist=False)
    
    def __repr__(self):
        return f'<User {self.name}>'

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_name = db.Column(db.String(100), nullable=False)
    cuisine_type = db.Column(db.String(50), nullable=False)
    tax_id = db.Column(db.String(20), unique=True, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    image_path = db.Column(db.String(255), nullable=True, default='default_restaurant.png')

    
    def __repr__(self):
        return f'<Restaurant {self.restaurant_name}>'
    
class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    category = db.Column(db.String(50), nullable=False, default = "diğer")  # e.g., 'appetizer', 'main course', 'dessert'
    
    restaurant = db.relationship('Restaurant', backref='menu_items')
    
    def __repr__(self):
        return f'<Menu Item {self.item_name}>'
    
class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    
    menu = db.relationship('Menu', backref='menu_items')
    
    def __repr__(self):
        return f'<Menu Item {self.item_name}>'
    
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='pending')  # pending, preparing, delivering, delivered, cancelled
    total_amount = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='orders')
    restaurant = db.relationship('Restaurant', backref='orders')

    #delivery_person edits
    delivery_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    delivery = db.relationship('User', foreign_keys=[delivery_id], backref='assigned_orders')   
    
    def __repr__(self):
        return f'<Order {self.id} - {self.status}>'

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu.id'), nullable=False)  # Changed from menu_item_id
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    # Relationships
    order = db.relationship('Order', backref='items')
    menu_item = db.relationship('Menu')  # Changed from MenuItem to Menu

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='cart')
    restaurant = db.relationship('Restaurant')
    
    def __repr__(self):
        return f'<Cart {self.id} - User {self.user_id}>'

# In models.py
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu.id'), nullable=False)  # This should match your actual column name
    quantity = db.Column(db.Integer, nullable=False, default=1)
    
    # Relationships
    cart = db.relationship('Cart', backref='items')
    menu_item = db.relationship('Menu')
    
    def __repr__(self):
        return f'<CartItem {self.id} - {self.quantity}x>'

class RestaurantReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='restaurant_reviews')
    restaurant = db.relationship('Restaurant', backref='reviews')
    
    def __repr__(self):
        return f'<RestaurantReview {self.id} - {self.rating} stars>'

class MenuItemReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='menu_item_reviews')
    menu_item = db.relationship('Menu', backref='reviews')
    
    def __repr__(self):
        return f'<MenuItemReview {self.id} - {self.rating} stars>'
    
class DeliveryPerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)  # e.g., bike, car
    license_plate = db.Column(db.String(20), unique=True, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User', backref='delivery_person')
    
    def __repr__(self):
        return f'<DeliveryPerson {self.id} - {self.user.name}>'
    