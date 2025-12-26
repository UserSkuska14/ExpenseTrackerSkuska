# Flask and DB
from flask import Flask, render_template, request, url_for,flash, redirect, Response, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_wtf import FlaskForm

#another
from datetime import date, datetime

#own
from utils import convert_date


# set FLASK_APP=наш гланый файл установка его по умолчанию при запуске
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'my_secret_key'# для флеш сооб
db = SQLAlchemy(app)

#модели для бд
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_date = db.Column(db.Date, default=date.today)

#модель юзера
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(90), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

class Base_Form(FlaskForm):...


# запуск базы данных
with app.app_context():
    db.create_all()

CATEGORIES = ["Food","Transport", "Utilities", "Rent", "Heath Care", "Clothing", "Investment"]


@app.before_request
def require_login():
    allowed_routes = {'login', 'register', 'static'}  # пути, где не нужна авторизация

    if request.endpoint not in allowed_routes and "user_id" not in session:
        return redirect(url_for("login"))


# обработка и переадресация на главнуб всех не указаных запросов
@app.route('/')
def index():
    # забираем даты 
    start_str = (request.args.get("start") or '').strip()
    end_str = (request.args.get("end") or '').strip()

    category = (request.args.get('category') or '').strip()

    view = (request.args.get('view') or 'table').strip()

    start_date = convert_date(start_str)
    end_date = convert_date(end_str)

    if start_date and end_date and start_date>end_date:
        flash("End date cannot be before start date")
        start_date = None
        end_date = None

    query_to_db = Expense.query
    if start_date:
        query_to_db = query_to_db.filter(Expense.created_date>=start_date)
    if end_date:
        query_to_db = query_to_db.filter(Expense.created_date<=end_date)
    if category:
        query_to_db = query_to_db.filter(Expense.category == category)

    expenses = query_to_db.order_by(Expense.created_date.desc(), Expense.id.desc()).all()
    total_expenses = round(sum(i.amount for i in expenses), 2)

    # данные для пирога
    categ_query = db.session.query(Expense.category, func.sum(Expense.amount))
    if start_date:
        categ_query = categ_query.filter(Expense.created_date>=start_date)
    if end_date:
        categ_query = categ_query.filter(Expense.created_date<=end_date)
    if category:
        categ_query = categ_query.filter(Expense.category == category)
    
    categ_row = categ_query.group_by(Expense.category).all()

    categ_labels = [lab for lab, _ in categ_row]
    categ_values = [round(float(v or 0), 2) for _, v in categ_row]

    # данные для обозначения по днях
    day_query = db.session.query(Expense.created_date, func.sum(Expense.amount))
    if start_date:
        day_query = day_query.filter(Expense.created_date>=start_date)
    if end_date:
        day_query = day_query.filter(Expense.created_date<=end_date)
    if category:
        day_query = day_query.filter(Expense.category == category)

    day_rows = day_query.group_by(Expense.created_date).order_by(Expense.created_date).all()
    day_labels = [day.isoformat() for day, _ in day_rows]
    day_values = [round(float(val or 0), 2) for _, val in day_rows]
    



    return render_template('index.html',
                           expenses=expenses,
                           categories=CATEGORIES,
                           category=category,
                           total_expenses=total_expenses,

                           date_today=date.today().isoformat(),
                           start_str=start_str,
                           end_str=end_str,

                           categ_labels=categ_labels,
                           categ_values=categ_values,

                           day_labels=day_labels,
                           day_values=day_values,
                           
                           view=view
                           )

# обработка запроса с добавлением категории
@app.route('/add', methods=["POST"])
def add():
    description= request.form.get('description', '').strip()
    amount_string = request.form.get('amount', '').strip()
    category = request.form.get('category', ).strip()
    date_add = request.form.get('date', '').strip()

    if '' in [description, category, date_add, amount_string]:
        # сообщение пользователю что он что-то не указал
        flash("Input valid data")
        return redirect(url_for('index'))
    
    try:
        amount = round(float(amount_string), 2)
        if amount<0:
            raise ValueError
    except ValueError:
        flash("Not valid amount used", 'error')
        amount=0

    try:
        if date_add:
            date_add = date.fromisoformat(date_add)
        else:
            date_add = date.today()
    except ValueError:
        flash("Date error, input valid date", 'error')
        date_add = date.today()


    new_user_model = Expense(
        description=description,
        amount=amount,
        category=category,
        created_date=date_add
    )

    db.session.add(new_user_model)
    db.session.commit()

    flash("Success added ✅", 'success')

    return redirect(url_for('index'))


@app.route('/delete/<expense_id>', methods=['POST'])
def delete(expense_id):
    print(expense_id)
    delete_model = Expense.query.get_or_404(expense_id)
    db.session.delete(delete_model)
    db.session.commit()
    flash("Expense success deleted", 'success')
    return redirect(url_for('index'))


@app.route('/export.csv')
def export_csv():
    start_str = (request.args.get("start") or '').strip()
    end_str = (request.args.get("end") or '').strip()
    category = (request.args.get('category') or '').strip()# выбранная категория

    start_date = convert_date(start_str)
    end_date = convert_date(end_str)

    query_to_db = Expense.query
    if start_date:
        query_to_db = query_to_db.filter(Expense.created_date>=start_date)
    if end_date:
        query_to_db = query_to_db.filter(Expense.created_date<=end_date)
    if category:
        query_to_db = query_to_db.filter(Expense.category == category)

    expenses = Expense.query.order_by(Expense.created_date, Expense.id).all()
    # CSV header
    lines = ["date, description, category, amount"]
    for e in expenses:
        lines.append(f"{e.created_date.isoformat()}, {e.description}, {e.category}, {e.amount:.2f} ")

    csv_data = '\n'.join(lines)
    fname_start = start_date or 'all'
    fname_end = end_date or 'all'
    file_name = f'expenses_{fname_start}_to_{fname_end}.csv'
    return Response(
        csv_data, 
        headers={
            "Content-Type":'text/csv',
            "Content-Disposition":f'attachment; filename={file_name}',
        }
    )


@app.route('/edit/<int:expense_id>', methods=['GET'])
def edit(expense_id):
    e = Expense.query.get_or_404(expense_id)
    return render_template('edit.html', expense=e, categories=CATEGORIES, today=date.today().isoformat())

@app.route('/edit/<int:expense_id>', methods=['POST'])
def edit_post(expense_id):
    e = Expense.query.get_or_404(expense_id)
    description = (request.form.get("description") or '').strip()
    category = (request.form.get("category") or '').strip()
    amount_str = (request.form.get("amount") or '').strip()
    change_date = (request.form.get("change_date") or '').strip()

    # Валидация
    if '' in [description,category,amount_str,change_date,]:
        flash("All fields are required", "error")
        return redirect(url_for('edit'), expense_id=expense_id)
    
    try:
        amount = round(float(amount_str or 0), 2)
        if amount<=0:
            raise ValueError
    except:
        flash("Invalid amount", "error")
        return redirect(url_for('edit'), expense_id=expense_id)
    
    try:
        change_date = datetime.strptime(change_date, "%Y-%m-%d").date() if change_date else date.today()
    except ValueError:
        change_date = date.today()
    
    # Обновляем объект
    e.description = description
    e.category = category
    e.amount = amount
    e.created_date = change_date
    db.session.commit()

    flash('"Expense updated ✅"', 'success')
    return redirect(url_for('index'))


@app.route("/register", methods=["GET", "POST"])
def register():
    form = Base_Form()
    if request.method == "POST":
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()
        password1 = request.form.get("password1").strip()

        if User.query.filter_by(email=email).first():
            flash("Email already registered")
            return redirect(url_for('register'))
        
        if password != password1:
            flash("Passwords do not match")
            return redirect(url_for('register'))
        
        new_user = User(email=email, password=password)

        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully")
        return redirect(url_for("login"))

    return render_template('register.html', form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = Base_Form()
    if request.method == "POST":
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()

        user = User.query.filter_by(email=email).first()

        if not user or user.password != password:
            flash("Invalid email or password")
            return redirect(url_for("login"))
        session["user_id"] = user.id
        flash("Logged in successfully")
        return redirect(url_for("index"))

    return render_template('login.html', form=form)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out")
    return redirect(url_for("login"))


if __name__ == '__main__':
    app.run()