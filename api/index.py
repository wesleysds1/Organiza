from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import errors
import bcrypt
import os

# Configuração do Flask
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = '@Deusefiel1'
CORS(app)

# Configuração do Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Modelo de usuário para autenticação
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

# Função para carregar usuário para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if user:
                return User(id=user["id"], username=user["username"], role=user["role"])
    return None

# Função para conectar ao banco de dados
def connect_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("A variável de ambiente DATABASE_URL não está configurada.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

try:
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            app.logger.info("Conexão com o banco de dados bem-sucedida.")
except Exception as e:
    app.logger.error(f"Erro ao conectar ao banco de dados: {e}")
    raise


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

# Rota inicial
@app.route("/")
def home():
    return redirect(url_for("login"))

# Rota de login
@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            app.logger.debug(f"Dados recebidos: username={username}, password={password}")

            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                    user = cur.fetchone()
                    app.logger.debug(f"Resultado da consulta para username={username}: {user}")

            if user and bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
                user_obj = User(id=user["id"], username=user["username"], role=user["role"])
                login_user(user_obj)
                return redirect(url_for("dashboard"))
            else:
                flash("Usuário ou senha incorretos.", "login_error")

        return render_template("login.html")
    except Exception as e:
        app.logger.error(f"Erro na rota de login: {e}")
        return f"Erro no servidor: {e}", 500

@app.context_processor
def inject_user_role():
    if current_user.is_authenticated:  # Verifica se o usuário está logado
        return {'role': current_user.role}
    return {'role': None}

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
    try:
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
    except Exception as e:
        return f"Erro ao carregar o dashboard: {e}", 500

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
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", 
                                (username, hashed_password, role))
                    conn.commit()
            flash("Usuário adicionado com sucesso!", "dashboard_success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            flash(f"Erro ao adicionar usuário: {e}", "dashboard_error")

    return render_template("add_user.html")

# Rota para adicionar produtos
@app.route("/add_product", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        try:
            name = request.form["name"]
            sku = request.form["sku"]
            quantity = int(request.form["quantity"])

            # Corrige a formatação do preço para evitar erros de conversão
            price = float(
                request.form["price"]
                .replace("R$", "")
                .replace("\xa0", "")
                .replace(".", "")
                .replace(",", ".")
                .strip()
            )

            supplier = request.form["supplier"]
            entry_date = request.form["entry_date"]  # Captura a data da entrada

            with connect_db() as conn:
                with conn.cursor() as cur:
                    # Verifica se o produto já existe
                    cur.execute("SELECT id, quantity, price FROM products WHERE name = %s AND sku = %s", (name, sku))
                    existing_product = cur.fetchone()

                    if existing_product:
                        # Produto existente: Atualiza a quantidade e o preço médio
                        product_id = existing_product["id"]
                        current_quantity = existing_product["quantity"]
                        current_price = existing_product["price"]

                        # Calcula a nova quantidade e o novo preço médio
                        new_quantity = current_quantity + quantity
                        new_price = ((current_quantity * current_price) + (quantity * price)) / new_quantity

                        # Atualiza a tabela `products`
                        cur.execute(
                            """
                            UPDATE products SET quantity = %s, price = %s WHERE id = %s
                            """,
                            (new_quantity, new_price, product_id),
                        )

                        # Adiciona uma nova entrada na tabela `product_entries`
                        cur.execute(
                            """
                            INSERT INTO product_entries (product_id, entry_date, quantity, price)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (product_id, entry_date, quantity, price),
                        )
                    else:
                        # Produto novo: Insere na tabela `products`
                        cur.execute(
                            """
                            INSERT INTO products (name, sku, quantity, price, supplier)
                            VALUES (%s, %s, %s, %s, %s) RETURNING id
                            """,
                            (name, sku, quantity, price, supplier),
                        )
                        product_id = cur.fetchone()["id"]

                        # Adiciona a primeira entrada na tabela `product_entries`
                        cur.execute(
                            """
                            INSERT INTO product_entries (product_id, entry_date, quantity, price)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (product_id, entry_date, quantity, price),
                        )

                    conn.commit()

            flash("Produto adicionado com sucesso!", "success")
            return redirect(url_for("dashboard"))

        except ValueError as e:
            flash(f"Erro ao processar valores numéricos: {e}", "error")
            return redirect(url_for("add_product"))
        except Exception as e:
            flash(f"Ocorreu um erro ao adicionar o produto: {e}", "error")
            return redirect(url_for("add_product"))

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
    try:
        product = None
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM products WHERE id = %s", (id,))
                product = cur.fetchone()

        if not product:
            return "Produto não encontrado.", 404

        if request.method == "POST":
            name = request.form["name"]
            quantity = int(request.form["quantity"])
            price = request.form["price"].replace("R$", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
            supplier = request.form["supplier"]

            try:
                price = float(price)  # Converte o preço para float
            except ValueError:
                flash("O preço fornecido está em um formato inválido.", "error")
                return redirect(url_for("update_product", id=id))

            with connect_db() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE products SET name = %s, quantity = %s, price = %s, supplier = %s WHERE id = %s",
                        (name, quantity, price, supplier, id)
                    )
                    conn.commit()

            flash("Produto atualizado com sucesso!", "success")
            return redirect(url_for("dashboard"))

        # Converta o produto para um dicionário e ajuste o preço para moeda brasileira
        product = dict(product)
        product["price"] = f"R$ {float(product['price']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return render_template("edit_product.html", product=product)
    except Exception as e:
        app.logger.error(f"Erro ao editar o produto: {e}")
        return f"Erro ao editar o produto: {e}", 500
    
@app.route("/delete_product/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                # Verifica se o produto existe antes de tentar excluir
                cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
                product = cur.fetchone()

                if not product:
                    flash("Produto não encontrado.", "error")
                    return redirect(url_for("dashboard"))

                # Exclui o produto
                cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
                conn.commit()

        flash("Produto excluído com sucesso!", "success")
        return redirect(url_for("dashboard"))
    except Exception as e:
        app.logger.error(f"Erro ao excluir produto: {e}")
        flash(f"Erro ao excluir produto: {e}", "error")
        return redirect(url_for("dashboard"))

@app.route("/reports")
@login_required
def reports():
    try:
        # Obter os dados para o gráfico de status
        with connect_db() as conn:
            with conn.cursor() as cur:
                # Obter dados de status dos produtos
                cur.execute("""
                    SELECT 
                        SUM(CASE WHEN quantity <= 15 THEN 1 ELSE 0 END) AS low,
                        SUM(CASE WHEN quantity > 15 AND quantity <= 30 THEN 1 ELSE 0 END) AS medium,
                        SUM(CASE WHEN quantity > 30 THEN 1 ELSE 0 END) AS ok
                    FROM products
                """)
                status_data = cur.fetchone()

                # Obter dados de entradas mensais
                cur.execute("""
                    SELECT 
                        TO_CHAR(entry_date, 'YYYY-MM') AS month,
                        SUM(quantity) AS total_quantity,
                        SUM(quantity * price) AS total_value
                    FROM product_entries
                    GROUP BY month
                    ORDER BY month
                """)
                monthly_data = cur.fetchall()

                # Obter dados de produtos por fornecedor
                cur.execute("""
                    SELECT supplier, COUNT(*) AS total_products
                    FROM products
                    GROUP BY supplier
                    ORDER BY total_products DESC
                """)
                supplier_data = cur.fetchall()

                # Obter gastos totais por mês
                cur.execute("""
                    SELECT 
                        TO_CHAR(entry_date, 'YYYY-MM') AS month,
                        SUM(quantity * price) AS total_spent
                    FROM product_entries
                    GROUP BY month
                    ORDER BY month
                """)
                total_spent_data = cur.fetchall()

        # Formatar os dados para o gráfico de status
        formatted_status = {
            "low": status_data["low"],
            "medium": status_data["medium"],
            "ok": status_data["ok"]
        }

        # Formatar os dados mensais
        formatted_monthly = [
            {
                "month": row["month"],
                "total_quantity": row["total_quantity"],
                "total_value": f"R$ {row['total_value']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            }
            for row in monthly_data
        ]

        # Formatar os dados de fornecedores
        formatted_supplier = [
            {"supplier": row["supplier"], "total_products": row["total_products"]}
            for row in supplier_data
        ]

        # Formatar os gastos totais por mês
        formatted_total_spent = [
            {
                "month": row["month"],
                "total_spent": f"R$ {row['total_spent']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            }
            for row in total_spent_data
        ]

        return render_template(
            "reports.html",
            status_data=formatted_status,
            monthly_data=formatted_monthly,
            supplier_data=formatted_supplier,
            total_spent_data=formatted_total_spent,
        )
    except Exception as e:
        app.logger.error(f"Erro ao gerar relatórios: {e}")
        return f"Erro ao gerar relatórios: {e}", 500


@app.route("/api/product_status_summary")
@login_required
def product_status_summary():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE quantity <= 15) AS low,
                        COUNT(*) FILTER (WHERE quantity > 15 AND quantity <= 30) AS medium,
                        COUNT(*) FILTER (WHERE quantity > 30) AS ok
                    FROM products;
                """)
                result = cur.fetchone()

                # Log para depuração
                app.logger.info(f"Resumo de status: {result}")

                return jsonify({
                    "low": result["low"],
                    "medium": result["medium"],
                    "ok": result["ok"]
                })
    except Exception as e:
        app.logger.error(f"Erro ao obter resumo de status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/entries_by_month")
@login_required
def entries_by_month():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        TO_CHAR(entry_date, 'YYYY-MM') AS month,
                        COUNT(*) AS total_entries,
                        COALESCE(SUM(quantity * price), 0) AS total_value
                    FROM product_entries
                    GROUP BY TO_CHAR(entry_date, 'YYYY-MM')
                    ORDER BY MIN(entry_date);
                """)
                data = cur.fetchall()

                formatted_data = [
                    {
                        "month": row["month"],
                        "total_entries": row["total_entries"],
                        "total_value": row["total_value"]
                    }
                    for row in data
                ]
        return jsonify(formatted_data)
    except Exception as e:
        app.logger.error(f"Erro ao obter entradas por mês: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/products_by_supplier", methods=["GET"])
@login_required
def products_by_supplier():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT supplier, COUNT(*) AS product_count
                    FROM products
                    GROUP BY supplier
                    ORDER BY product_count DESC
                """)
                data = cur.fetchall()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/total_spent_by_month", methods=["GET"])
@login_required
def total_spent_by_month():
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        TO_CHAR(entry_date, 'YYYY-MM') AS month,
                        SUM(quantity * price) AS total_spent
                    FROM product_entries
                    GROUP BY month
                    ORDER BY month
                """)
                data = cur.fetchall()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/edit_user", methods=["GET", "POST"])
@login_required
def edit_user():
    if current_user.role != "admin":
        flash("Acesso negado. Permissões de administrador são necessárias.", "dashboard_error")
        return redirect(url_for("dashboard"))

    users = []
    try:
        # Garantir que o cursor esteja dentro do contexto
        with connect_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, role FROM users")
                users = cur.fetchall()

        if request.method == "POST":
            user_id = request.form["id"]
            username = request.form["username"]
            password = request.form["password"]
            role = request.form["role"]

            hashed_password = None
            if password:  # Somente atualiza a senha se fornecida
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Atualizar os dados do usuário
            with connect_db() as conn:
                with conn.cursor() as cur:
                    if hashed_password:
                        cur.execute(
                            "UPDATE users SET username = %s, password = %s, role = %s WHERE id = %s",
                            (username, hashed_password, role, user_id)
                        )
                    else:
                        cur.execute(
                            "UPDATE users SET username = %s, role = %s WHERE id = %s",
                            (username, role, user_id)
                        )
                    conn.commit()

            flash("Usuário atualizado com sucesso!", "dashboard_success")
            return redirect(url_for("dashboard"))

        # Renderizar a página com os usuários carregados
        return render_template("edit_user.html", users=users)
    except Exception as e:
        flash(f"Erro ao editar usuário: {e}", "error")
        return redirect(url_for("dashboard"))

@app.route("/delete_user/<int:id>", methods=["POST"])
@login_required
def delete_user(id):
    if current_user.role != "admin":
        flash("Acesso negado. Permissões de administrador são necessárias.", "dashboard_error")
        return redirect(url_for("dashboard"))

    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (id,))
    flash("Usuário excluído com sucesso!", "dashboard_success")

    return redirect(url_for("edit_user"))

@app.route("/api/products", methods=["GET"])
@login_required
def get_products():
    search_query = request.args.get("search", "").lower()
    try:
        with connect_db() as conn:
            with conn.cursor() as cur:
                if search_query:
                    cur.execute("""
                        SELECT * FROM products WHERE 
                        LOWER(name) LIKE %s OR LOWER(sku) LIKE %s
                    """, (f"%{search_query}%", f"%{search_query}%"))
                else:
                    cur.execute("SELECT * FROM products")
                
                products = cur.fetchall()  # Capture os dados antes de sair do `with`

        product_list = []
        for product in products:
            product_dict = dict(product)
            quantity = product_dict["quantity"]
            if quantity <= 15:
                product_dict["status"] = "Baixo"
            elif quantity <= 30:
                product_dict["status"] = "Médio"
            else:
                product_dict["status"] = "OK"
            product_list.append(product_dict)

        return jsonify(product_list)
    except Exception as e:
        app.logger.error(f"Erro ao buscar produtos: {e}")
        return jsonify({"error": f"Erro ao buscar produtos: {e}"}), 500
    
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

@app.route("/about")
def about():
    return render_template("about.html")

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store"
    return response

# Executar o aplicativo
if __name__ == "__main__":
    app.run(debug=True)
