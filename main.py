from flask import Flask, render_template, request, redirect, url_for, flash, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Product, Cart, CartItem, Category
from functools import wraps
from flask_wtf import CSRFProtect   
from sqlalchemy import or_
import os, uuid

# --------------------------------------------------------- konfiguracia ----------------------------------------------------------- #

app = Flask(__name__, instance_relative_config=True)

app.secret_key = "VenomSnakeisgoated_6741"
csrf = CSRFProtect(app)

# -------------------------------------------------------- monacemta bazis konfiguracia--------------------------------------------- #

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///products.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# with app.app_context():
    # db.create_all()

# with app.app_context():
    # user = User.query.filter_by(email="datochtb@gmail.com").first()
    # user.is_admin = True
    # db.session.commit()

# -------------------------------------------------------- fotoebis atvirtvis konfiguracia ----------------------------------------- #

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --------------------------------------------------------------- flask_login ------------------------------------------------------ #

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------------------------------------------------- sachiro funqciebi ------------------------------------------------------------ #

def get_or_create_cart(user):
    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.commit()
    return cart

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("ამის გაკეთების უფლება მხოლოდ ადმინებს აქვთ.")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

def save_image(file):
    if not file or file.filename == "":
        return None

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash("არასწორი ფაილის ტიპი.")
        return None

    filename = f"{uuid.uuid4().hex}{ext}"
    file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
    return filename

# -------------------------------------------------- WEBSAITIS GVERDEBIS FUNQCIEBI ------------------------------------------------- #

# --------------------------------------------------- mtavari gverdi --------------------------------------------------------------- #

@app.route("/")
def home():
    return render_template("OverclockersGeorgia.html")

# ---------------------------------------------PROFILEBTAN DAKAVSHIREBULI FUNQCIRBI ------------------------------------------------ #

# --------------------------------------------------- registracia ------------------------------------------------------------------ #

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("მომხმარებელი მაგ ელ-ფოსტით უკვე არსებობს.")
            return redirect(url_for("signup"))

        user = User(name=name, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("პროფილი შეიქმნა!")
        return redirect(url_for("home"))

    return render_template("Signup.html")

# --------------------------------------------------- profilshi shesvla ------------------------------------------------------------ #

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash(f"კეთილი იყოს თქვენი დაბრუნება, {user.name}!")
            return redirect(url_for("home"))

        flash("ელ-ფოსტა ან პაროლი არასწორია.")
        return redirect(url_for("login"))

    return render_template("Login.html")

# --------------------------------------------------- profilidan gamosvla ---------------------------------------------------------- #

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("თქვენ გამოხვედით პროფილიდან.")
    return redirect(url_for("home"))

# ------------------------------------------- PRODUQTEBTAN DAKAVSHIREBULI FUNQCIEBI ------------------------------------------------ #

# ------------------------------------------- produqtebi marketze ------------------------------------------------------------------ #

@app.route("/products")
def products():
    query = request.args.get("q")

    if query:
        products_list = Product.query.filter(
            Product.in_person.is_(False),
            or_(
                Product.title.ilike(f"%{query}%"),
                Product.description.ilike(f"%{query}%")
            )
        ).all()
    else:
        products_list = Product.query.filter_by(in_person=False).all()

    return render_template("products.html", products=products_list)

@app.route("/products/<int:id>")
def product_detail(id):
    product = Product.query.get_or_404(id)
    return render_template("product_detail.html", product=product)

# ---------------------------------------------------- produqtis damateba ---------------------------------------------------------- #

@app.route("/add-general-product", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        price = request.form.get("price", type=float)
        image = request.files.get("image")

        image_filename = save_image(image) if image else None

        product = Product(
            title=title,
            description=description,
            price=price,
            image_filename=image_filename,
            user=current_user,
            category_id=None
        )

        db.session.add(product)
        db.session.commit()

        flash("პროდუქტი დაემატა!")
        return redirect(url_for("products"))

    return render_template("add_product.html")

# ---------------------------------------------------- produqtis washla ------------------------------------------------------------ #

@app.route("/delete-product/<int:id>", methods=["POST"])
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)

    if product.user_id != current_user.id and not current_user.is_admin:
        flash("არ გაქვთ პროდუქტის წაშლის უფლება.")
        return redirect(url_for("products"))

    if product.image_filename:
        image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], product.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(product)
    db.session.commit()
    flash("პროდუქტი წარმატებით წაიშალა!")
    return redirect(request.referrer or url_for("products"))

# ---------------------------------------- kategoriis shignit produqtis damateba (mxolod admins sheulia) --------------------------- #

@app.route("/add-product", methods=["GET", "POST"])
@login_required
@admin_required
def add_in_person_product():
    categories = Category.query.all()
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        price = request.form.get("price", type=float)
        category_id = request.form.get("category_id", type=int)
        image = request.files.get("image")

        if category_id is None:
            flash("გთხოვთ, აირჩიოთ კატეგორია.")
            return redirect(request.url)
        
        image_filename = save_image(image) if image else None

        product = Product(
            title=title,
            description=description,
            price=price,
            image_filename=image_filename,
            user=current_user,
            category_id=category_id,
            in_person=True
        )
        db.session.add(product)
        db.session.commit()
        flash("პროდუქტი დამატებული იქნა ფსევდო-ფილიალში!")
        category = Category.query.get(category_id)
        if category:
            return redirect(url_for("category_products", slug=category.slug))
        else:
            return redirect(url_for("products"))

    return render_template("add_in_person_product.html", categories=categories)

# ---------------------------------------------KATEGORIEBTAN DAKAVSHIREBULI FUNQCIEBI ---------------------------------------------- #

# ------------------------------------------------------- kategoriebi -------------------------------------------------------------- #

@app.route("/categories")
def categories():
    categories_list = Category.query.all()
    return render_template("categories.html", categories=categories_list)

@app.route("/categories/<slug>")
def category_products(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    products_list = Product.query.filter_by(category_id=category.id).all()
    return render_template("category_products.html", category=category, products=products_list)

# ----------------------------------------- kategoriis damateba (mxolod admins sheulia) -------------------------------------------- #

@app.route("/admin/add-category", methods=["GET", "POST"])
@login_required
@admin_required
def add_category():
    if request.method == "POST":
        name = request.form["name"]
        slug = request.form["slug"]
        image = request.files.get("image")

        image_filename = save_image(image) if image else None

        category = Category(name=name, slug=slug, image_filename=image_filename)
        db.session.add(category)
        db.session.commit()
        flash(f"კატეგორია '{name}' წარმატებით იქნა დამატებული!")
        return redirect(url_for("categories"))

    return render_template("add_category.html")

# ---------------------------------------- kategoriis washla (mxolod admins sheulia) ----------------------------------------------- #

@app.route("/admin/delete-category/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)

    for product in category.products:
        if product.image_filename:
            product_image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], product.image_filename)
            if os.path.exists(product_image_path):
                os.remove(product_image_path)

    if category.image_filename:
        category_image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], category.image_filename)
        if os.path.exists(category_image_path):
            os.remove(category_image_path)

    db.session.delete(category)
    db.session.commit()

    flash(f"კატეგორია '{category.name}' და მისი პროდუქტები წარმატებით იქნა წაშლილი!")
    return redirect(url_for("categories"))

# ---------------------------------------------- KALATASTAN DAKAVSHIREBULI FUNQCIEBI ----------------------------------------------- #

# --------------------------------------------------------- kalata ----------------------------------------------------------------- #

@app.route("/cart")
@login_required
def cart():
    cart_obj = get_or_create_cart(current_user)
    total = sum(item.quantity * item.product.price for item in cart_obj.items)
    return render_template("cart.html", cart=cart_obj, total=total)

# --------------------------------------------------------- kalatashi damateba ----------------------------------------------------- #

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    cart_obj = get_or_create_cart(current_user)
    item = CartItem.query.filter_by(cart_id=cart_obj.id, product_id=product_id).first()

    if item:
        item.quantity += 1
    else:
        item = CartItem(cart_id=cart_obj.id, product_id=product_id, quantity=1)
        db.session.add(item)

    db.session.commit()
    flash("პროდუქტი დამატებული იქნა კალათაში!")
    return redirect(url_for("cart"))

# --------------------------------------------------------- kalatidan washla ------------------------------------------------------- #

@app.route("/remove-from-cart/<int:item_id>", methods=["POST"])
@login_required
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user_id != current_user.id:
        flash("არ გაქვთ კალათის ნახვის უფლება.")
        return redirect(url_for("cart"))

    db.session.delete(item)
    db.session.commit()
    flash("პროდუქტი წარმატებით წაიშალა კალათიდან!")
    return redirect(url_for("cart"))

# --------------------------------------------------------- CHECKOUT --------------------------------------------------------------- #

@app.route("/checkout")
@login_required
def checkout():
    return render_template("checkout.html")

@app.route("/checkout-complete", methods=["POST"])
@login_required
def checkout_complete():
    cart_obj = get_or_create_cart(current_user)
    for item in cart_obj.items:
        db.session.delete(item)

    db.session.commit()

    flash("ოპერაცია დადასტურებულია! გმადლობთ შეძენისთვის!")
    return redirect(url_for("home"))

# --------------------------------------------------------- appis gashveba --------------------------------------------------------- #

if __name__ == "__main__":
    app.run(host = "0.0.0.0")