from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Restaurant, Order, OrderItem, Menu, MenuItem, Cart, CartItem, RestaurantReview, MenuItemReview, DeliveryPerson, CreditCard
from flask_migrate import Migrate
from flask_mail import Mail, Message
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, func, and_



app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # some security process not much important in our case

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yemeksepeti.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Flask-Migrate'i başlat
migrate = Migrate(app, db)

# Create tables within app context
with app.app_context():
    db.create_all()

# Mail ayarları
app.config['MAIL_SERVER'] = 'smtp.yandex.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True  # SSL kullanılmalı
app.config['MAIL_USE_TLS'] = False  # TLS kullanılmamalı
app.config['MAIL_USERNAME'] = 'yemeksepetieren@yandex.com'
app.config['MAIL_PASSWORD'] = 'memjgrlmoisojypc'  # Okul projesi için sorun değil
app.config['MAIL_DEFAULT_SENDER'] = 'yemeksepetieren@yandex.com'

mail = Mail(app)

# Kullanıcı tipi kontrol fonksiyonları //// kimin hangi sayfaya girip giremeyeceğini kontrol eden decoratorlar
# bizim 3 kullanıcı tipimiz var admin, restaurant ve user
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'admin':
            flash('Bu sayfaya erişmek için admin yetkisi gereklidir', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def restaurant_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'restaurant':
            flash('Bu sayfaya erişmek için restoran yetkisi gereklidir', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Admin dashboard page
@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    # Count pending restaurant approvals
    pending_count = Restaurant.query.filter_by(is_approved=False).count()
    return render_template("admin_dashboard.html", pending_count=pending_count)

# Restaurant dashboard page
@app.route("/restaurant/dashboard")
@login_required
@restaurant_required
def restaurant_dashboard():
    # Giriş yapmış restoranın bilgilerini getir
    restaurant = Restaurant.query.filter_by(user_id=session['user_id']).first()
    return render_template("restaurant_dashboard.html", restaurant=restaurant)


# Delivery person access control decorator
def delivery_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'delivery':
            flash('Bu sayfaya erişmek için kurye yetkisi gereklidir', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/dashboard/delivery")
@login_required
@delivery_required
def delivery_dashboard():
    if "user_id" not in session or session.get("user_type") != "delivery":
        flash("Yetkisiz erişim.", "danger")
        return redirect(url_for("login"))

    delivery_person = DeliveryPerson.query.filter_by(user_id=session["user_id"]).first()

    return render_template("delivery_dashboard.html", delivery_person=delivery_person)

@app.route("/delivery/orders")
def delivery_orders():
    if "user_id" not in session or session.get("user_type") != "delivery":
        flash("Yetkisiz erişim.", "danger")
        return redirect(url_for("login"))

    delivery_id = session["user_id"]
    orders = Order.query.filter_by(delivery_id=delivery_id).order_by(Order.order_date.desc()).all()

    return render_template("delivery_orders.html", orders=orders)


@app.route("/delivery/profile/edit", methods=["GET", "POST"])
def edit_delivery_profile():
    if "user_id" not in session or session.get("user_type") != "delivery":
        flash("Yetkisiz erişim.", "danger")
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    delivery_person = DeliveryPerson.query.filter_by(user_id=user.id).first()

    if delivery_person is None:
        flash("Kurye profili bulunamadı. Lütfen yöneticinize başvurun.", "danger")
        return redirect(url_for("delivery_dashboard"))

    if request.method == "POST":
        user.name = request.form.get("name")
        user.email = request.form.get("email")
        user.phone = request.form.get("phone")
        delivery_person.vehicle_type = request.form.get("vehicle_type")
        delivery_person.license_plate = request.form.get("license_plate")

        db.session.commit()
        flash("Profil bilgileri başarıyla güncellendi.", "success")
        return redirect(url_for("delivery_dashboard"))

    return render_template("edit_delivery_profile.html", user=user, delivery=delivery_person)



@app.route("/")
def home():
    # Get query parameters for filtering and sorting
    cuisine_filter = request.args.get('cuisine', 'all')
    rating_filter = request.args.get('rating', 'all')
    sort_by = request.args.get('sort_by', 'rating')
    sort_dir = request.args.get('sort_dir', 'desc')
    
    # Base query - only approved restaurants
    restaurants_query = Restaurant.query.filter_by(is_approved=True)
    
    # Apply filters
    if cuisine_filter != 'all':
        restaurants_query = restaurants_query.filter(Restaurant.cuisine_type == cuisine_filter)
    
    if rating_filter != 'all' and rating_filter.replace('.', '', 1).isdigit():
        min_rating = float(rating_filter)
        restaurants_query = restaurants_query.filter(Restaurant.rating >= min_rating)
    
    # Apply sorting
    if sort_by == 'name':
        if sort_dir == 'asc':
            restaurants_query = restaurants_query.order_by(Restaurant.restaurant_name.asc())
        else:
            restaurants_query = restaurants_query.order_by(Restaurant.restaurant_name.desc())
    elif sort_by == 'rating':
        if sort_dir == 'asc':
            restaurants_query = restaurants_query.order_by(Restaurant.rating.asc())
        else:
            restaurants_query = restaurants_query.order_by(Restaurant.rating.desc())
    elif sort_by == 'cuisine':
        if sort_dir == 'asc':
            restaurants_query = restaurants_query.order_by(Restaurant.cuisine_type.asc())
        else:
            restaurants_query = restaurants_query.order_by(Restaurant.cuisine_type.desc())
    
    # Execute query
    restaurants = restaurants_query.all()
    
    # Get all unique cuisine types for filter dropdown
    cuisine_types = db.session.query(Restaurant.cuisine_type).distinct().all()
    cuisine_types = [cuisine[0] for cuisine in cuisine_types if cuisine[0] is not None]    
    # Rating options for filter
    rating_options = ['3.0', '3.5', '4.0', '4.5']
    
    return render_template(
        "index.html", 
        restaurants=restaurants,
        cuisine_types=cuisine_types,
        rating_options=rating_options,
        current_cuisine=cuisine_filter,
        current_rating=rating_filter,
        current_sort_by=sort_by,
        current_sort_dir=sort_dir
    )

# Giriş sayfası
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        # Check if user exists in database
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['logged_in'] = True
            session['user_type'] = user.user_type
            session['user_id'] = user.id
            session['email'] = user.email
            session['name'] = user.name
            
            flash(f'Hoş geldiniz, {user.name}!', 'success')
            
            if user.user_type == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.user_type == 'restaurant':
                return redirect(url_for('restaurant_dashboard'))
            else:
                return redirect(url_for('home'))
        else:
            flash('Geçersiz email veya şifre!', 'danger')
    
    return render_template("login.html")

# Çıkış yap
@app.route("/logout")
def logout():
    session.clear()
    flash('Başarıyla çıkış yaptınız', 'success')
    return redirect(url_for('home'))

#Kullanıcı kaydı
@app.route("/register/user", methods=["GET", "POST"])
def register_user():
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Şifreler eşleşmiyor!', 'danger')
            return redirect(url_for('register_user'))
        
        # Check if email is already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Bu email adresi zaten kayıtlı!', 'danger')
            return redirect(url_for('register_user'))
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            phone=phone,
            address=address,
            user_type='user'
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Kullanıcı hesabınız başarıyla oluşturuldu!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Kayıt sırasında bir hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('register_user'))
    
    return render_template("register_user.html")

@app.route("/register/delivery", methods=["GET", "POST"])
def register_delivery():
    if request.method == "POST":
        name = request.form.get("full_name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        phone = request.form.get("phone")
        vehicle_type = request.form.get("vehicle_type")
        license_plate = request.form.get("license_plate")

        # Form validasyonu
        if password != confirm_password:
            flash("Şifreler uyuşmuyor.", "danger")
            return redirect(url_for("register_delivery"))

        if not vehicle_type:
            flash("Lütfen araç tipi seçin.", "danger")
            return redirect(url_for("register_delivery"))
            
        if not license_plate:
            flash("Lütfen plaka numarası girin.", "danger")
            return redirect(url_for("register_delivery"))

        # Email kontrol
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Bu e-posta adresi zaten kullanılıyor.", "warning")
            return redirect(url_for("register_delivery"))
            
        # Plaka kontrol
        existing_plate = DeliveryPerson.query.filter_by(license_plate=license_plate).first()
        if existing_plate:
            flash("Bu plaka numarası zaten kayıtlı.", "warning")
            return redirect(url_for("register_delivery"))

        # Kullanıcı oluştur
        hashed_password = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            phone=phone,
            user_type="delivery"
        )
        db.session.add(new_user)
        db.session.flush()  # ID almak için önce flush edin
        
        # Kurye bilgilerini oluştur
        new_delivery = DeliveryPerson(
            user_id=new_user.id,
            vehicle_type=vehicle_type,
            license_plate=license_plate,
            is_available=True,
            is_approved=False  # Yeni kuryeler onay beklemeli
        )
        
        db.session.add(new_delivery)
        db.session.commit()

        flash("Kurye kaydınız başarıyla oluşturuldu! Hesabınız onaylandıktan sonra giriş yapabilirsiniz.", "success")
        return redirect(url_for("login"))

    return render_template("register_delivery.html")


# Restoran kaydı
@app.route("/register/restaurant", methods=["GET", "POST"])
def register_restaurant():
    if request.method == "POST":
        owner_name = request.form.get('owner_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        address = request.form.get('address')
        restaurant_name = request.form.get('restaurant_name')
        cuisine_type = request.form.get('cuisine_type')
        tax_id = request.form.get('tax_id')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Şifreler eşleşmiyor!', 'danger')
            return redirect(url_for('register_restaurant'))
        
        # Check if email is already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Bu email adresi zaten kayıtlı!', 'danger')
            return redirect(url_for('register_restaurant'))
        
        # Check if tax_id is already registered
        existing_restaurant = Restaurant.query.filter_by(tax_id=tax_id).first()
        if existing_restaurant:
            flash('Bu vergi numarası zaten kayıtlı!', 'danger')
            return redirect(url_for('register_restaurant'))
        
        try:
            # Create new user with restaurant type
            hashed_password = generate_password_hash(password)
            new_user = User(
                name=owner_name,
                email=email,
                password=hashed_password,
                phone=phone,
                address=address,
                user_type='restaurant'
            )
            
            db.session.add(new_user)
            db.session.flush()  # Get the user ID before committing
            
            # Create new restaurant linked to this user
            new_restaurant = Restaurant(
                user_id=new_user.id,
                restaurant_name=restaurant_name,
                cuisine_type=cuisine_type,
                tax_id=tax_id,
                is_approved=False  # Needs admin approval
            )
            
            db.session.add(new_restaurant)
            db.session.commit()
            
            flash('Restoran hesabınız başarıyla oluşturuldu! Admin onayından sonra aktif olacaktır.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Kayıt sırasında bir hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('register_restaurant'))
    
    return render_template("register_restaurant.html")

# Admin kaydı
@app.route("/register/admin", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        admin_code = request.form.get('admin_code')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Şifreler eşleşmiyor!', 'danger')
            return redirect(url_for('register_admin'))
        
        # Verify admin code (in a real application, this would be more secure)
        if admin_code != "secret_admin_code":
            flash('Geçersiz admin kodu!', 'danger')
            return redirect(url_for('register_admin'))
        
        # Check if email is already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Bu email adresi zaten kayıtlı!', 'danger')
            return redirect(url_for('register_admin'))
        
        # Create new admin user
        hashed_password = generate_password_hash(password)
        new_admin = User(
            name=name,
            email=email,
            password=hashed_password,
            user_type='admin'
        )
        
        try:
            db.session.add(new_admin)
            db.session.commit()
            flash('Admin hesabınız başarıyla oluşturuldu!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Kayıt sırasında bir hata oluştu: {str(e)}', 'danger')
            return redirect(url_for('register_admin'))
    
    return render_template("register_admin.html")

# Restaurant approval action (approve/reject)
@app.route("/admin/restaurant-action/<int:restaurant_id>", methods=["POST"])
@login_required
@admin_required
def restaurant_action(restaurant_id):
    action = request.form.get('action')
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    if action == 'approve':
        restaurant.is_approved = True
        db.session.commit()
        flash(f'{restaurant.restaurant_name} onaylandı!', 'success')
    elif action == 'reject':
        # You might want to add a notification system later
        # For now, let's just remove the restaurant and its owner
        user_id = restaurant.user_id
        db.session.delete(restaurant)
        user = User.query.get(user_id)
        db.session.delete(user)
        db.session.commit()
        flash(f'{restaurant.restaurant_name} reddedildi!', 'danger')
    
    return redirect(url_for('restaurant_approvals'))

# Restaurant approval page
@app.route("/admin/restaurant-approvals", methods=["GET"])
@login_required
@admin_required
def restaurant_approvals():
    # Get all pending restaurant approvals
    pending_restaurants = Restaurant.query.filter_by(is_approved=False).all()
    # Join with user data to get owner information
    restaurant_data = []
    for restaurant in pending_restaurants:
        owner = User.query.get(restaurant.user_id)
        restaurant_data.append({
            'restaurant': restaurant,
            'owner': owner
        })
    return render_template("restaurant_approvals.html", restaurant_data=restaurant_data)

# Admin orders page
@app.route("/admin/orders", methods=["GET"])
@login_required
@admin_required
def admin_orders():
    # Get filters from query parameters
    status_filter = request.args.get('status', 'all')
    restaurant_id = request.args.get('restaurant_id', 'all')
    sort_by = request.args.get('sort_by', 'date')
    sort_dir = request.args.get('sort_dir', 'desc')
    
    # Base query
    orders_query = Order.query
    
    # Apply filters
    if status_filter != 'all':
        orders_query = orders_query.filter(Order.status == status_filter)
    
    if restaurant_id != 'all' and restaurant_id.isdigit():
        orders_query = orders_query.filter(Order.restaurant_id == int(restaurant_id))
    
    # Apply sorting
    if sort_by == 'date':
        if sort_dir == 'asc':
            orders_query = orders_query.order_by(Order.order_date.asc())
        else:
            orders_query = orders_query.order_by(Order.order_date.desc())
    elif sort_by == 'amount':
        if sort_dir == 'asc':
            orders_query = orders_query.order_by(Order.total_amount.asc())
        else:
            orders_query = orders_query.order_by(Order.total_amount.desc())
    elif sort_by == 'status':
        if sort_dir == 'asc':
            orders_query = orders_query.order_by(Order.status.asc())
        else:
            orders_query = orders_query.order_by(Order.status.desc())
    
    # Execute query
    orders = orders_query.all()
    
    # Get all restaurants for the filter dropdown
    restaurants = Restaurant.query.filter_by(is_approved=True).all()
    
    # Define possible statuses for filter dropdown
    statuses = ['pending', 'preparing', 'delivering', 'delivered', 'cancelled']
    
    return render_template(
        "admin_orders.html", 
        orders=orders, 
        restaurants=restaurants,
        statuses=statuses,
        current_status=status_filter,
        current_restaurant=restaurant_id,
        current_sort_by=sort_by,
        current_sort_dir=sort_dir
    )

@app.route("/restaurant/<int:restaurant_id>")
def restaurant_menu(restaurant_id):
    # Get restaurant information
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Only show approved restaurants to users
    if not restaurant.is_approved and ('user_type' not in session or session['user_type'] != 'admin'):
        flash('Bu restoran henüz onaylanmamıştır.', 'danger')
        return redirect(url_for('home'))
    
    # Get menu items from the restaurant
    menu_items = Menu.query.filter_by(restaurant_id=restaurant_id, is_available=True).all()
    
    # Get restaurant reviews
    restaurant_reviews = RestaurantReview.query.filter_by(restaurant_id=restaurant_id).order_by(RestaurantReview.created_at.desc()).all()
    
    # Get user's existing restaurant review if logged in
    user_restaurant_review = None
    if 'logged_in' in session and session['user_type'] == 'user':
        user_restaurant_review = RestaurantReview.query.filter_by(
            user_id=session['user_id'],
            restaurant_id=restaurant_id
        ).first()
    
    # Get user's existing ratings for menu items if logged in
    user_menu_ratings = {}
    if 'logged_in' in session and session['user_type'] == 'user':
        user_ratings = MenuItemReview.query.filter_by(user_id=session['user_id']).all()
        for rating in user_ratings:
            user_menu_ratings[rating.menu_id] = rating.rating
    
    # Calculate average rating for each menu item
    for item in menu_items:
        item_ratings = MenuItemReview.query.filter_by(menu_id=item.id).all()
        if item_ratings:
            total_rating = sum(review.rating for review in item_ratings)
            item.avg_rating = round(total_rating / len(item_ratings), 1)
        else:
            item.avg_rating = None
    
    # Get cart info if user is logged in
    cart_items = []
    cart_total = 0
    cart_count = 0
    
    if 'logged_in' in session and session['user_type'] == 'user':
        cart = Cart.query.filter_by(user_id=session['user_id'], restaurant_id=restaurant_id).first()
        if cart:
            for cart_item in cart.items:
                menu_item = cart_item.menu_item
                item_total = menu_item.price * cart_item.quantity
                cart_total += item_total
                cart_count += cart_item.quantity
                
                cart_items.append({
                    'id': cart_item.id,
                    'menu_item': menu_item,
                    'quantity': cart_item.quantity,
                    'item_total': item_total
                })
    
    return render_template(
        "restaurant_menu.html",
        restaurant=restaurant,
        menu_items=menu_items,
        cart_items=cart_items,
        cart_total=cart_total,
        cart_count=cart_count,
        restaurant_reviews=restaurant_reviews,
        user_restaurant_review=user_restaurant_review,
        user_menu_ratings=user_menu_ratings
    )

# Add item to cart
@app.route("/add-to-cart", methods=["POST"])
@login_required
def add_to_cart():
    if session['user_type'] != 'user':
        flash('Sadece normal kullanıcılar sepete ürün ekleyebilir.', 'danger')
        return redirect(url_for('home'))
    
    menu_item_id = request.form.get('menu_item_id')
    quantity = int(request.form.get('quantity', 1))
    
    # Get the menu item
    menu_item = Menu.query.get_or_404(menu_item_id)
    restaurant_id = menu_item.restaurant_id
    
    # Check if user already has a cart for this restaurant
    cart = Cart.query.filter_by(user_id=session['user_id'], restaurant_id=restaurant_id).first()
    
    # If no cart exists, create one
    if not cart:
        cart = Cart(user_id=session['user_id'], restaurant_id=restaurant_id)
        db.session.add(cart)
        db.session.flush()
    
    # Use menu_id instead of menu_item_id
    cart_item = CartItem.query.filter_by(cart_id=cart.id, menu_id=menu_item_id).first()
    
    # If item exists, update quantity, otherwise create new cart item
    if cart_item:
        cart_item.quantity += quantity
    else:
        # Use menu_id instead of menu_item_id
        cart_item = CartItem(cart_id=cart.id, menu_id=menu_item_id, quantity=quantity)
        db.session.add(cart_item)
    
    try:
        db.session.commit()
        flash(f'{menu_item.item_name} sepete eklendi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Bir hata oluştu: {str(e)}', 'danger')
    
    return redirect(url_for('restaurant_menu', restaurant_id=restaurant_id))

# View cart
@app.route("/cart")
@login_required
def view_cart():
    if session['user_type'] != 'user':
        flash('Sadece normal kullanıcılar sepeti görüntüleyebilir.', 'danger')
        return redirect(url_for('home'))
    
    # Get user's cart
    cart = Cart.query.filter_by(user_id=session['user_id']).first()
    
    if not cart or not cart.items:
        return render_template("cart.html", cart=None, items=[], restaurant=None, total=0)
    
    # Get cart items with details
    items = []
    total = 0
    
    for cart_item in cart.items:
        menu_item = cart_item.menu_item
        item_total = menu_item.price * cart_item.quantity
        total += item_total
        
        items.append({
            'id': cart_item.id,
            'menu_item': menu_item,
            'quantity': cart_item.quantity,
            'item_total': item_total
        })
    
    # Get restaurant info
    restaurant = Restaurant.query.get(cart.restaurant_id)
    
    return render_template("cart.html", cart=cart, items=items, restaurant=restaurant, total=total)

# Update cart item quantity
@app.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def update_cart_item(item_id):
    if session['user_type'] != 'user':
        flash('Bu işlem için yetkiniz yok.', 'danger')
        return redirect(url_for('home'))
    
    quantity = int(request.form.get('quantity', 1))
    
    # Get cart item
    cart_item = CartItem.query.get_or_404(item_id)
    
    # Verify ownership
    cart = Cart.query.get(cart_item.cart_id)
    if cart.user_id != session['user_id']:
        flash('Bu işlem için yetkiniz yok.', 'danger')
        return redirect(url_for('view_cart'))
    
    # Update quantity or remove if quantity is 0
    if quantity > 0:
        cart_item.quantity = quantity
        flash('Sepet güncellendi.', 'success')
    else:
        db.session.delete(cart_item)
        flash('Ürün sepetten çıkarıldı.', 'success')
    
    db.session.commit()
    
    # Check if cart is empty, delete if it is
    remaining_items = CartItem.query.filter_by(cart_id=cart.id).count()
    if remaining_items == 0:
        db.session.delete(cart)
        db.session.commit()
    
    return redirect(url_for('view_cart'))

# Remove item from cart
@app.route("/cart/remove/<int:item_id>")
@login_required
def remove_cart_item(item_id):
    if session['user_type'] != 'user':
        flash('Bu işlem için yetkiniz yok.', 'danger')
        return redirect(url_for('home'))
    
    # Get cart item
    cart_item = CartItem.query.get_or_404(item_id)
    
    # Verify ownership
    cart = Cart.query.get(cart_item.cart_id)
    if cart.user_id != session['user_id']:
        flash('Bu işlem için yetkiniz yok.', 'danger')
        return redirect(url_for('view_cart'))
    
    # Remove the item
    db.session.delete(cart_item)
    db.session.commit()
    
    # Check if cart is empty, delete if it is
    remaining_items = CartItem.query.filter_by(cart_id=cart.id).count()
    if remaining_items == 0:
        db.session.delete(cart)
        db.session.commit()
        flash('Sepetiniz boş.', 'info')
    else:
        flash('Ürün sepetten çıkarıldı.', 'success')
    
    return redirect(url_for('view_cart'))

#şifre unutma route'u
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Rastgele 6 haneli bir kod oluştur
            import random
            import string
            reset_code = ''.join(random.choices(string.digits, k=6))
            
            # Kodun geçerlilik süresini belirle (30 dakika)
            expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
            
            # Kullanıcının bilgilerini güncelle
            user.reset_code = reset_code
            user.reset_code_expiry = expiry
            db.session.commit()
            
            # E-posta gönder
            try:
                msg = Message("Şifre Sıfırlama", recipients=[email])
                msg.body = f"Şifre sıfırlama kodunuz: {reset_code}\nBu kod 30 dakika boyunca geçerlidir."
                mail.send(msg)
                flash("Şifre sıfırlama kodu e-posta adresinize gönderildi.", "success")
                return redirect(url_for("verify_reset_code", email=email))
            except Exception as e:
                db.session.rollback()  # Kod kaydını geri al
                flash(f"E-posta gönderilirken bir hata oluştu: {str(e)}", "danger")
                return redirect(url_for("forgot_password"))
        else:
            flash("Bu e-posta adresi ile kayıtlı bir hesap bulunamadı.", "danger")
    
    return render_template("forgot_password.html")


# Şifre sıfırlama kodunu doğrulama
@app.route("/verify-reset-code", methods=["GET", "POST"])
def verify_reset_code():
    email = request.args.get("email")
    
    if not email:
        flash("Geçersiz istek.", "danger")
        return redirect(url_for('login'))
    
    if request.method == "POST":
        reset_code = request.form.get("reset_code")
        user = User.query.filter_by(email=email, reset_code=reset_code).first()
        
        # Ensure reset_code_expiry is timezone-aware
        now = datetime.now(timezone.utc)
        
        if user and user.reset_code_expiry:
            # Make sure reset_code_expiry is timezone-aware
            if user.reset_code_expiry.tzinfo is None:
                user.reset_code_expiry = user.reset_code_expiry.replace(tzinfo=timezone.utc)
            
            if user.reset_code_expiry > now:
                # Kod geçerli
                return redirect(url_for("reset_password", email=email, code=reset_code))
        
        flash("Geçersiz veya süresi dolmuş kod.", "danger")
    
    return render_template("verify_reset_code.html", email=email)



# Şifre sıfırlama
@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.args.get("email")
    code = request.args.get("code")
    
    if not email or not code:
        flash("Geçersiz istek.", "danger")
        return redirect(url_for("login"))
    
    user = User.query.filter_by(email=email, reset_code=code).first()
    
    # Ensure reset_code_expiry is timezone-aware
    now = datetime.now(timezone.utc)
    
    if not user or not user.reset_code_expiry:
        flash("Geçersiz kod.", "danger")
        return redirect(url_for("login"))
    
    # Make sure reset_code_expiry is timezone-aware
    if user.reset_code_expiry.tzinfo is None:
        user.reset_code_expiry = user.reset_code_expiry.replace(tzinfo=timezone.utc)
    
    if user.reset_code_expiry < now:
        flash("Süresi dolmuş kod.", "danger")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if password != confirm_password:
            flash("Şifreler eşleşmiyor.", "danger")
        else:
            # Şifreyi güncelle
            hashed_password = generate_password_hash(password)
            user.password = hashed_password
            user.reset_code = None
            user.reset_code_expiry = None
            db.session.commit()
            
            flash("Şifreniz başarıyla değiştirildi. Yeni şifrenizle giriş yapabilirsiniz.", "success")
            return redirect(url_for("login"))
    
    return render_template("reset_password.html", email=email, code=code)



# Menu Management Routes to add to app.py

# Restaurant menu management page
@app.route("/restaurant/menu-management")
@login_required
@restaurant_required
def menu_management():
    # Get the restaurant associated with the logged-in user
    restaurant = Restaurant.query.filter_by(user_id=session['user_id']).first()
    
    if not restaurant:
        flash('Restoran bilgisi bulunamadı', 'danger')
        return redirect(url_for('restaurant_dashboard'))
    
    # Get all menu items for this restaurant
    menu_items = Menu.query.filter_by(restaurant_id=restaurant.id).all()
    
    return render_template("menu_management.html", restaurant=restaurant, menu_items=menu_items)

# Add new menu item
@app.route("/restaurant/add-menu-item", methods=["POST"])
@login_required
@restaurant_required
def add_menu_item():
    # Debug için form verilerini yazdır
    print("FORM DATA:", request.form)
    
    # Get the restaurant associated with the logged-in user
    restaurant = Restaurant.query.filter_by(user_id=session['user_id']).first()
    
    if not restaurant:
        flash('Restoran bilgisi bulunamadı', 'danger')
        return redirect(url_for('restaurant_dashboard'))
    
    # Get form data
    item_name = request.form.get('item_name')
    description = request.form.get('description')
    price = request.form.get('price')
    # Kategori bilgisini doğru şekilde al
    category = request.form.get('category')
    is_available = request.form.get('is_available') == 'True'
    
    # Create new menu item
    menu_item = Menu(
        restaurant_id=restaurant.id,
        item_name=item_name,
        description=description,
        price=float(price),
        category=category,  # Kategori bilgisini kaydet
        is_available=is_available
    )
    
    try:
        db.session.add(menu_item)
        db.session.commit()
        flash(f'{item_name} başarıyla eklendi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Bir hata oluştu: {str(e)}', 'danger')
    
    return redirect(url_for('menu_management'))

# Edit menu item page
@app.route("/restaurant/edit-menu-item/<int:item_id>", methods=["GET", "POST"])
@login_required
@restaurant_required
def edit_menu_item(item_id):
    # Debug için form verilerini yazdır (POST isteği olduğunda)
    if request.method == "POST":
        print("EDIT FORM DATA:", request.form)
    
    # Get the restaurant associated with the logged-in user
    restaurant = Restaurant.query.filter_by(user_id=session['user_id']).first()
    
    if not restaurant:
        flash('Restoran bilgisi bulunamadı', 'danger')
        return redirect(url_for('restaurant_dashboard'))
    
    # Get the menu item
    menu_item = Menu.query.get_or_404(item_id)
    
    # Verify that this menu item belongs to the logged-in restaurant
    if menu_item.restaurant_id != restaurant.id:
        flash('Bu işlem için yetkiniz yok', 'danger')
        return redirect(url_for('menu_management'))
    
    if request.method == "POST":
        # Update the menu item with new values
        menu_item.item_name = request.form.get('item_name')
        menu_item.description = request.form.get('description')
        menu_item.price = float(request.form.get('price'))
        # Kategori bilgisini güncelle
        menu_item.category = request.form.get('category')
        menu_item.is_available = request.form.get('is_available') == 'True'
        
        try:
            db.session.commit()
            flash(f'{menu_item.item_name} başarıyla güncellendi!', 'success')
            return redirect(url_for('menu_management'))
        except Exception as e:
            db.session.rollback()
            flash(f'Bir hata oluştu: {str(e)}', 'danger')
    
    return render_template("edit_menu_item.html", menu_item=menu_item)

# Delete menu item
@app.route("/restaurant/delete-menu-item/<int:item_id>", methods=["POST"])
@login_required
@restaurant_required
def delete_menu_item(item_id):
    # Get the restaurant associated with the logged-in user
    restaurant = Restaurant.query.filter_by(user_id=session['user_id']).first()
    
    if not restaurant:
        flash('Restoran bilgisi bulunamadı', 'danger')
        return redirect(url_for('restaurant_dashboard'))
    
    # Get the menu item
    menu_item = Menu.query.get_or_404(item_id)
    
    # Verify that this menu item belongs to the logged-in restaurant
    if menu_item.restaurant_id != restaurant.id:
        flash('Bu işlem için yetkiniz yok', 'danger')
        return redirect(url_for('menu_management'))
    
    try:
        item_name = menu_item.item_name
        db.session.delete(menu_item)
        db.session.commit()
        flash(f'{item_name} başarıyla silindi!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Bir hata oluştu: {str(e)}', 'danger')
    
    return redirect(url_for('menu_management'))

@app.route("/checkout")
@login_required
def checkout():
    # Get user's cart
    cart = Cart.query.filter_by(user_id=session['user_id']).first()
    
    if not cart or not cart.items:
        flash('Sepetiniz boş.', 'warning')
        return redirect(url_for('home'))
    
    # Get cart items with details
    items = []
    total = 0
    
    for cart_item in cart.items:
        menu_item = cart_item.menu_item
        item_total = menu_item.price * cart_item.quantity
        total += item_total
        
        items.append({
            'id': cart_item.id,
            'menu_item': menu_item,
            'quantity': cart_item.quantity,
            'item_total': item_total
        })
    
    # Get restaurant info
    restaurant = Restaurant.query.get(cart.restaurant_id)
    
    return render_template("checkout.html", cart=cart, items=items, restaurant=restaurant, total=total)

@app.route("/place-order", methods=["POST"])
@login_required
def place_order():
    # Get user's cart
    cart = Cart.query.filter_by(user_id=session['user_id']).first()
    
    if not cart or not cart.items:
        flash('Sepetiniz boş.', 'warning')
        return redirect(url_for('home'))
    
    # Get delivery address and payment method
    delivery_address = request.form.get('address')
    payment_method = request.form.get('payment_method')
    notes = request.form.get('notes', '')
    
    # Calculate total
    total = 0
    for cart_item in cart.items:
        menu_item = cart_item.menu_item
        total += menu_item.price * cart_item.quantity
    
    # Create order
    new_order = Order(
        user_id=session['user_id'],
        restaurant_id=cart.restaurant_id,
        total_amount=total,
        delivery_address=delivery_address,
        status='pending'
    )
    
    db.session.add(new_order)
    db.session.flush()  # Get the new order ID
    
    # Create order items
    for cart_item in cart.items:
        menu_item = cart_item.menu_item
        order_item = OrderItem(
            order_id=new_order.id,
            menu_id=cart_item.menu_id,  # Use menu_id instead of menu_item_id
            quantity=cart_item.quantity,
            price=menu_item.price
        )
        db.session.add(order_item)
    
    # Delete cart and items
    cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
    for item in cart_items:
        db.session.delete(item)
    
    db.session.delete(cart)
    db.session.commit()
    
    flash('Siparişiniz başarıyla alındı!', 'success')
    return redirect(url_for('home'))

# Restoran değerlendirme ekleme route'u
@app.route("/restaurant/<int:restaurant_id>/review", methods=["POST"])
@login_required
def add_restaurant_review(restaurant_id):
    if session['user_type'] != 'user':
        flash('Yalnızca müşteriler değerlendirme yapabilir.', 'danger')
        return redirect(url_for('restaurant_menu', restaurant_id=restaurant_id))
    
    rating = int(request.form.get('rating', 0))
    comment = request.form.get('comment', '')
    
    # Validate the rating
    if rating < 1 or rating > 5:
        flash('Geçersiz puanlama. Lütfen 1-5 arası bir değer giriniz.', 'danger')
        return redirect(url_for('restaurant_menu', restaurant_id=restaurant_id))
    
    # Check if user already reviewed this restaurant
    existing_review = RestaurantReview.query.filter_by(
        user_id=session['user_id'],
        restaurant_id=restaurant_id
    ).first()
    
    if existing_review:
        # Update existing review
        existing_review.rating = rating
        existing_review.comment = comment
        existing_review.created_at = datetime.now(timezone.utc)
        flash('Değerlendirmeniz güncellendi!', 'success')
    else:
        # Create new review
        new_review = RestaurantReview(
            user_id=session['user_id'],
            restaurant_id=restaurant_id,
            rating=rating,
            comment=comment
        )
        db.session.add(new_review)
        flash('Değerlendirmeniz için teşekkürler!', 'success')
    
    # Update restaurant average rating
    reviews = RestaurantReview.query.filter_by(restaurant_id=restaurant_id).all()
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        avg_rating = total_rating / len(reviews)
        
        restaurant = Restaurant.query.get(restaurant_id)
        restaurant.rating = round(avg_rating, 1)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Bir hata oluştu: {str(e)}', 'danger')
    
    return redirect(url_for('restaurant_menu', restaurant_id=restaurant_id))

# Menü öğesi puanlama route'u
@app.route("/menu-item/<int:item_id>/rate", methods=["POST"])
@login_required
def rate_menu_item(item_id):
    if session['user_type'] != 'user':
        flash('Yalnızca müşteriler puanlama yapabilir.', 'danger')
        return redirect(url_for('home'))
    
    rating = int(request.form.get('rating', 0))
    
    # Validate the rating
    if rating < 1 or rating > 5:
        flash('Geçersiz puanlama. Lütfen 1-5 arası bir değer giriniz.', 'danger')
        return redirect(url_for('home'))
    
    # Get the menu item
    menu_item = Menu.query.get_or_404(item_id)
    restaurant_id = menu_item.restaurant_id
    
    # Check if user already rated this menu item
    existing_rating = MenuItemReview.query.filter_by(
        user_id=session['user_id'],
        menu_id=item_id
    ).first()
    
    if existing_rating:
        # Update existing rating
        existing_rating.rating = rating
        existing_rating.created_at = datetime.now(timezone.utc)
        flash('Puanlamanız güncellendi!', 'success')
    else:
        # Create new rating
        new_rating = MenuItemReview(
            user_id=session['user_id'],
            menu_id=item_id,
            rating=rating
        )
        db.session.add(new_rating)
        flash('Puanlamanız için teşekkürler!', 'success')
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Bir hata oluştu: {str(e)}', 'danger')
    
    return redirect(url_for('restaurant_menu', restaurant_id=restaurant_id))

# Restaurant bilgilerini düzenleme sayfası
@app.route("/restaurant/edit-profile", methods=["GET", "POST"])
@login_required
@restaurant_required
def edit_restaurant_profile():
    # Get the restaurant associated with the logged-in user
    restaurant = Restaurant.query.filter_by(user_id=session['user_id']).first()
    
    if not restaurant:
        flash('Restoran bilgisi bulunamadı', 'danger')
        return redirect(url_for('restaurant_dashboard'))
    
    if request.method == "POST":
        # Get form data
        restaurant_name = request.form.get('restaurant_name')
        cuisine_type = request.form.get('cuisine_type')
        
        # Update information
        restaurant.restaurant_name = restaurant_name
        restaurant.cuisine_type = cuisine_type
        
        # Image upload processing (if present)
        if 'restaurant_image' in request.files:
            image_file = request.files['restaurant_image']
            if image_file.filename != '':
                # Create secure filename
                import os
                from werkzeug.utils import secure_filename
                
                # Check upload folder and create if doesn't exist
                # Change to consistent location: static/images/restaurants
                upload_folder = os.path.join(app.root_path, 'static', 'images', 'restaurants')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                # Create secure filename and save
                filename = secure_filename(f"restaurant_{restaurant.id}_{image_file.filename}")
                filepath = os.path.join(upload_folder, filename)
                image_file.save(filepath)
                
                # Update image path in database - store just the filename
                restaurant.image_path = filename
        
        try:
            db.session.commit()
            flash('Restoran bilgileri başarıyla güncellendi!', 'success')
            return redirect(url_for('restaurant_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Bir hata oluştu: {str(e)}', 'danger')
    
    return render_template("edit_restaurant_profile.html", restaurant=restaurant)


@app.route("/cart")
@login_required
def cart():
    if 'user_id' not in session:
        flash("Sepeti görüntülemek için giriş yapmalısınız.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    cart_items = CartItem.query.join(Cart).filter(Cart.user_id == user_id).all()

    return render_template("cart.html", cart_items=cart_items)

# Search route - duplicate fonksiyon tanımlarını bu tek fonksiyonda birleştirdik
@app.route("/search")
def search():
    search_query = request.args.get('query', '')

    if not search_query:
        return redirect(url_for('home'))

    # Büyük-küçük harf duyarsız arama için
    search_term = f"%{search_query.lower()}%"

    # 1. Restoran ismine göre arama
    restaurants_by_name = Restaurant.query.filter(
        and_(
            Restaurant.is_approved == True,
            func.lower(Restaurant.restaurant_name).like(search_term)
        )
    ).all()

    # 2. Menü içeriğine göre arama - restoran ID'leri
    restaurant_ids_by_menu = db.session.query(Menu.restaurant_id).filter(
        func.lower(Menu.item_name).like(search_term)
    ).distinct().all()

    # List comprehension ile ID'leri al
    restaurant_ids = [id[0] for id in restaurant_ids_by_menu]

    # Bu ID'lere sahip restoranları getir
    restaurants_by_menu = []
    if restaurant_ids:  # Empty list check to avoid SQL errors
        restaurants_by_menu = Restaurant.query.filter(
            and_(
                Restaurant.is_approved == True,
                Restaurant.id.in_(restaurant_ids)
            )
        ).all()

    # İki sonuç kümesini birleştir ve tekrarları kaldır
    seen = set()
    all_restaurants = []

    # İlk liste - restoran isimlerine göre eşleşenler
    for restaurant in restaurants_by_name:
        if restaurant.id not in seen:
            all_restaurants.append(restaurant)
            seen.add(restaurant.id)

    # İkinci liste - menü içeriğine göre eşleşenler
    for restaurant in restaurants_by_menu:
        if restaurant.id not in seen:
            all_restaurants.append(restaurant)
            seen.add(restaurant.id)

    return render_template(
        "search_results.html",
        restaurants=all_restaurants,
        search_query=search_query)


@app.route("/restaurant/orders")
@login_required
@restaurant_required
def restaurant_orders():
    """
    Restoran sahibinin kendi restoranına ait siparişleri görmesini sağlar.
    """
    try:
        # Restoran bilgilerini al
        restaurant_user_id = session.get('user_id')
        if not restaurant_user_id:
            flash('Restoran bilgilerine erişilemedi. Lütfen tekrar giriş yapın.', 'danger')
            return redirect(url_for('login'))

        restaurant = Restaurant.query.filter_by(user_id=restaurant_user_id).first()
        if not restaurant:
            flash('Restoran bulunamadı.', 'danger')
            return redirect(url_for('restaurant_dashboard'))

        # Siparişleri çek (eager loading ile ilişkili verileri de yükle)
        orders = db.session.query(Order)\
                  .filter_by(restaurant_id=restaurant.id)\
                  .join(User, User.id == Order.user_id)\
                  .options(db.joinedload(Order.items).joinedload(OrderItem.menu_item))\
                  .order_by(Order.order_date.desc())\
                  .all()
        
        # Detaylı hata ayıklama için
        print(f"Bulunan sipariş sayısı: {len(orders)}")
        
        return render_template("restaurant_orders.html", orders=orders, restaurant_name=restaurant.restaurant_name)

    except Exception as e:
        import traceback
        # Detaylı hata mesajını görüntüle
        print(f"Hata: {str(e)}")
        print(traceback.format_exc())  # Hata izini görüntüle
        flash(f'Siparişleri yüklerken bir hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('restaurant_dashboard'))


@app.template_filter('status_color')
def status_color(status):
    colors = {
        'pending': 'warning',
        'preparing': 'info',
        'delivering': 'primary',
        'delivered': 'success',
        'cancelled': 'danger'
    }
    return colors.get(status, 'secondary')

@app.template_filter('status_text')
def status_text(status):
    texts = {
        'pending': 'Beklemede',
        'preparing': 'Hazırlanıyor',
        'delivering': 'Yolda',
        'delivered': 'Teslim Edildi',
        'cancelled': 'İptal Edildi'
    }
    return texts.get(status, status)


@app.route("/delivery/available-orders")
@login_required
@delivery_required
def available_orders():
    orders = Order.query.filter(
        Order.status == 'pending',
        Order.delivery_id == None
    ).order_by(Order.order_date.desc()).all()
    
    return render_template("available_orders.html", orders=orders)


@app.route("/delivery/claim-order/<int:order_id>", methods=["POST"])
@login_required
@delivery_required
def claim_order(order_id):
    order = Order.query.get_or_404(order_id)

    if order.status != "pending" or order.delivery_id is not None:
        flash("Bu sipariş zaten başkası tarafından alınmış veya uygun değil.", "warning")
        return redirect(url_for("available_orders"))

    order.delivery_id = session["user_id"]
    order.status = "delivering"

    db.session.commit()
    flash("Sipariş başarıyla üzerinize alındı.", "success")
    return redirect(url_for("delivery_orders"))


@app.route("/delivery/complete-order/<int:order_id>", methods=["POST"])
@login_required
@delivery_required
def complete_order(order_id):
    order = Order.query.get_or_404(order_id)

    if order.delivery_id != session["user_id"]:
        flash("Bu sipariş size ait değil!", "danger")
        return redirect(url_for("delivery_orders"))

    if order.status != "delivering":
        flash("Bu sipariş zaten teslim edilmiş veya iptal edilmiş.", "warning")
        return redirect(url_for("delivery_orders"))

    order.status = "delivered"
    db.session.commit()
    flash("Sipariş teslim edildi olarak işaretlendi.", "success")
    return redirect(url_for("delivery_orders"))


# Kredi Kartları sayfası
@app.route("/credit-cards")
@login_required
def credit_cards():
    if session['user_type'] != 'user':
        flash('Bu sayfaya erişmek için müşteri hesabı gereklidir.', 'danger')
        return redirect(url_for('home'))
    
    # Kullanıcının kredi kartlarını getir
    user_cards = CreditCard.query.filter_by(user_id=session['user_id']).all()
    
    # Yıl bilgisini template'e gönder (kart ekleme formu için)
    current_year = datetime.now().year
    
    return render_template(
        "credit_cards.html",
        credit_cards=user_cards,
        current_year=current_year
    )

# Kredi kartı ekleme
@app.route("/add-credit-card", methods=["POST"])
@login_required
def add_credit_card():
    if session['user_type'] != 'user':
        flash('Bu işlemi gerçekleştirmek için müşteri hesabı gereklidir.', 'danger')
        return redirect(url_for('home'))
    
    # Form verilerini al
    card_number = request.form.get('card_number').replace(" ", "")  # Boşlukları kaldır
    expiry_month = request.form.get('expiry_month')
    expiry_year = request.form.get('expiry_year')
    cvv = request.form.get('cvv')  # Güvenlik için veritabanında saklanmaz
    cardholder_name = request.form.get('cardholder_name')
    
    # Basit doğrulamalar
    if len(card_number) < 13 or len(card_number) > 19:
        flash('Geçersiz kart numarası.', 'danger')
        return redirect(url_for('credit_cards'))
    
    # Son 4 haneyi al
    last_four = card_number[-4:]
    
    # Aynı kart var mı kontrol et
    existing_card = CreditCard.query.filter_by(
        user_id=session['user_id'],
        last_four=last_four,
        expiry_month=expiry_month,
        expiry_year=expiry_year
    ).first()
    
    if existing_card:
        flash('Bu kart zaten kayıtlı.', 'warning')
        return redirect(url_for('credit_cards'))
    
    # İlk kart mı kontrol et (varsayılan olarak ayarlamak için)
    is_first_card = CreditCard.query.filter_by(user_id=session['user_id']).count() == 0
    
    # Yeni kredi kartını oluştur
    # Gerçek uygulamada kart numarası şifrelenir!
    new_card = CreditCard(
        user_id=session['user_id'],
        card_number=card_number,  # Üretim ortamında asla tam kart numarası saklanmamalı
        last_four=last_four,
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        cardholder_name=cardholder_name,
        is_default=is_first_card
    )
    
    try:
        db.session.add(new_card)
        db.session.commit()
        flash('Kredi kartı başarıyla eklendi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kart eklenirken bir hata oluştu: {str(e)}', 'danger')
    
    return redirect(url_for('credit_cards'))

# Kredi kartı silme
@app.route("/delete-credit-card/<int:card_id>", methods=["POST"])
@login_required
def delete_credit_card(card_id):
    if session['user_type'] != 'user':
        flash('Bu işlemi gerçekleştirmek için müşteri hesabı gereklidir.', 'danger')
        return redirect(url_for('home'))
    
    # Kartı bul
    card = CreditCard.query.get_or_404(card_id)
    
    # Kartın bu kullanıcıya ait olduğunu doğrula
    if card.user_id != session['user_id']:
        flash('Bu işlemi gerçekleştirmek için yetkiniz yok.', 'danger')
        return redirect(url_for('credit_cards'))
    
    # Silinen kart varsayılan ise ve başka kart varsa, yeni varsayılan belirle
    was_default = card.is_default
    
    try:
        db.session.delete(card)
        
        if was_default:
            # Başka kart var mı kontrol et
            remaining_card = CreditCard.query.filter_by(user_id=session['user_id']).first()
            if remaining_card:
                remaining_card.is_default = True
        
        db.session.commit()
        flash('Kredi kartı başarıyla silindi.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Kart silinirken bir hata oluştu: {str(e)}', 'danger')
    
    return redirect(url_for('credit_cards'))
def status_color(status):
    return {
        'pending': 'warning',
        'preparing': 'info',
        'on_delivery': 'primary',
        'delivered': 'success',
        'cancelled': 'danger'
    }.get(status, 'secondary')

def status_text(status):
    return {
        'pending': 'Beklemede',
        'preparing': 'Hazırlanıyor',
        'on_delivery': 'Yolda',
        'delivered': 'Teslim Edildi',
        'cancelled': 'İptal Edildi'
    }.get(status, 'Bilinmiyor')

app.jinja_env.globals.update(status_color=status_color)
app.jinja_env.globals.update(status_text=status_text)


@app.route("/orders")
@login_required
def user_orders():
    if session['user_type'] != 'user':
        flash('Bu sayfaya erişmek için müşteri hesabı gereklidir.', 'danger')
        return redirect(url_for('home'))

    orders = Order.query.filter_by(user_id=session['user_id']) \
        .order_by(Order.order_date.desc()) \
        .all()

    return render_template("user_orders.html", orders=orders)


if __name__ == "__main__":
    app.run(debug=True)