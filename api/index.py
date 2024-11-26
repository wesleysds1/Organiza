from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import errors
import bcrypt
import os

app = Flask(__name__)
app.secret_key = '@Deusefiel1'
CORS(app)

# Configuração do Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Função para conectar ao banco de dados
def connect_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não está configurada.")
    
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Inicializar o banco de dados
def init_db():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    sku TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    supplier TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user'
                );
            """)
            conn.commit()

# Inserir usuário de teste
def insert_test_user():
    with connect_db() as conn:
        with conn.cursor() as cur:
            hashed_password = bcrypt.hashpw("password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            try:
                cur.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO NOTHING;
                """, ("admin", hashed_password, "admin"))
                conn.commit()
            except errors.UniqueViolation:
                pass

@login_manager.user_loader
def load_user(user_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if user:
                return User(id=user["id"], username=user["username"], role=user["role"])
    return None

# Modelo de usuário para autenticação
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

# Rota inicial
@app.route("/")
def home():
    return redirect(url_for("login"))

# Rota de login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cur.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
            user_obj = User(id=user["id"], username=user["username"], role=user["role"])
            login_user(user_obj)
            return redirect(url_for("dashboard"))
        else:
            flash("Usuário ou senha incorretos.", "login_error")
            
    return render_template("login.html")

# Rota de logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# Rota para o dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM products")
            products = cur.fetchall()

    formatted_products = []
    for product in products:
        product = dict(product)
        try:
            price = float(product["price"])
            quantity = int(product["quantity"])
            product["price"] = f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            product["total"] = f"R$ {price * quantity:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            product["price"] = "R$ 0,00"
            product["total"] = "R$ 0,00"
        formatted_products.append(product)

    return render_template("dashboard.html", username=current_user.username, products=formatted_products)

# Rota para adicionar novo usuário
@app.route("/add_user", methods=["GET", "POST"])
@login_required
def add_user():
    if current_user.role != "admin":
        flash("Acesso negado. Permissões de administrador são necessárias.", "dashboard_error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = connect_db()
        try:
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, hashed_password.decode('utf-8'), role))
            conn.commit()
            flash("Usuário adicionado com sucesso!", "dashboard_success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Erro: O nome de usuário já existe.", "dashboard_error")
        finally:
            conn.close()

    return render_template("add_user.html")

# Rota para adicionar produtos
@app.route("/add_product", methods=["GET", "POST"])
@login_required
def add_product_page():
    if request.method == "POST":
        name = request.form["name"]
        sku = request.form["sku"]
        quantity = int(request.form["quantity"])
        price = float(request.form["price"].replace(",", "."))
        supplier = request.form["supplier"]

        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO products (name, sku, quantity, price, supplier)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, sku, quantity, price, supplier))
                conn.commit()
        flash("Produto adicionado com sucesso!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_product.html")


@app.route("/update_product", methods=["POST"])
@login_required
def edit_product():
    # Pegue os dados do formulário
    product_id = request.form.get("id")
    name = request.form.get("name")
    quantity = request.form.get("quantity")
    price = request.form.get("price")
    supplier = request.form.get("supplier")

    # Atualize o produto no banco de dados
    conn = connect_db()
    cur.execute("""
        UPDATE products SET name = %s, quantity = %s, price = %s, supplier = %s
        WHERE id = %s
    """, (name, int(quantity), float(price), supplier, int(product_id)))
    conn.commit()
    conn.close()

    # Mostre uma mensagem de sucesso
    flash("Produto atualizado com sucesso!", "success")
    return redirect(url_for("dashboard"))

# Rota para a página de edição do produto
@app.route("/edit_product/<int:id>", methods=["GET", "POST"])
@login_required
def update_product(id):
    conn = connect_db()
    product = cur.execute("SELECT * FROM products WHERE id = %s", (id,)).fetchone()
    conn.close()

    if not product:
        return "Produto não encontrado.", 404

    if request.method == "POST":
        # Atualizar os dados do produto
        name = request.form["name"]
        quantity = int(request.form["quantity"])
        price = request.form["price"].replace("R$", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
        supplier = request.form["supplier"]

        try:
            price = float(price)  # Converte o preço para float
        except ValueError:
            flash("O preço fornecido está em um formato inválido.", "error")
            return redirect(url_for("update_product", id=id))

        conn = connect_db()
        cur.execute(
            "UPDATE products SET name = %s, quantity = %s, price = %s, supplier = %s WHERE id = %s",
            (name, quantity, price, supplier, id)
        )
        conn.commit()
        conn.close()

        flash("Produto atualizado com sucesso!", "success")
        return redirect(url_for("dashboard"))

    # Garantir que `price` seja convertido para float antes de formatar
    product = dict(product)
    product["price"] = float(product["price"])
    product["price"] = f"R$ {product['price']:.2f}".replace(".", ",")  # Formatar como moeda brasileira
    product["total"] = f"R$ {float(product['price'].replace('R$', '').replace(',', '.')) * product['quantity']:.2f}".replace(".", ",")  # Calcular total formatado

    return render_template("edit_product.html", product=product)

@app.route("/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
                conn.commit()
        flash("Produto excluído com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao excluir produto: {e}", "error")
    return redirect(url_for("dashboard"))

@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html")


@app.route("/edit_user", methods=["GET", "POST"])
@login_required
def edit_user():
    if current_user.role != "admin":
        flash("Acesso negado. Permissões de administrador são necessárias.", "dashboard_error")
        return redirect(url_for("dashboard"))

    conn = connect_db()
    users = cur.execute("SELECT id, username, role FROM users").fetchall()
    conn.close()

    if request.method == "POST":
        user_id = request.form["id"]
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        conn = connect_db()
        if password:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            cur.execute("UPDATE users SET username = %s, password = %s, role = %s WHERE id = %s", 
                         (username, hashed_password.decode('utf-8'), role, user_id))
        else:
            cur.execute("UPDATE users SET username = %s, role = %s WHERE id = %s", 
                         (username, role, user_id))
        
        conn.commit()
        conn.close()
        flash("Usuário atualizado com sucesso!", "dashboard_success")
        return redirect(url_for("dashboard"))

    return render_template("edit_user.html", users=users)

@app.route("/delete_user/<int:id>", methods=["POST"])
@login_required
def delete_user(id):
    if current_user.role != "admin":
        flash("Acesso negado. Permissões de administrador são necessárias.", "dashboard_error")
        return redirect(url_for("dashboard"))

    conn = connect_db()
    cur.execute("DELETE FROM users WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash("Usuário excluído com sucesso!", "dashboard_success")
    return redirect(url_for("edit_user"))

@app.route("/api/products", methods=["GET"])
@login_required
def get_products():
    search_query = request.args.get("search", "").lower()
    conn = connect_db()

    if search_query:
        products = cur.execute("""
            SELECT * FROM products WHERE 
            LOWER(name) LIKE %s OR LOWER(sku) LIKE %s
        """, (f"%{search_query}%", f"%{search_query}%")).fetchall()
    else:
        products = cur.execute("SELECT * FROM products").fetchall()

    conn.close()

    product_list = []

    # Adicionar lógica para categorizar os produtos com base na quantidade
    for product in products:
        product_dict = dict(product)
        quantity = product_dict["quantity"]

        if quantity <= 20:
            product_dict["status"] = "Baixo"
        elif quantity <= 50:
            product_dict["status"] = "Médio"
        else:
            product_dict["status"] = "OK"

        product_list.append(product_dict)

    return jsonify(product_list)

# Rota para modificar ou deletar um produto
@app.route("/api/products/<int:id>", methods=["PUT", "DELETE"])
@login_required
def modify_product(id):
    conn = connect_db()
    if request.method == "PUT":
        data = request.get_json()
        cur.execute(
            "UPDATE products SET name=%s, sku=%s, quantity=%s, price=%s, supplier=%s WHERE id=%s",
            (data["name"], data["sku"], data["quantity"], data["price"], data["supplier"], id)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Produto atualizado com sucesso!"})

    elif request.method == "DELETE":
        cur.execute("DELETE FROM products WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Produto excluído com sucesso!"})

@app.route("/test_dashboard")
def test_dashboard():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="/static/css/dashboard.css">
    </head>
    <body class="dashboard-page">
        <div class="card">
            <div class="card-header">Testando CSS do Dashboard</div>
            <div class="card-body">Conteúdo do Card</div>
        </div>
    </body>
    </html>
    '''


# Executar o aplicativo
if __name__ == "__main__":
    app.run(debug=True)

