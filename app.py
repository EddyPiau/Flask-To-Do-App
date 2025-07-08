from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
import hashlib # For password hashing
from datetime import datetime, date 
import sqlite3

app = Flask(__name__)

app.secret_key = 'your_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' #redirect to login if not authorised

#Create a database connection if not exist 

def init_db():
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )''')


    # Create tasks table if it doesn't exist
    c.execute(''' CREATE TABLE IF NOT EXISTS tasks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              content Text NOT NULL,
              done BOOLEAN NOT NULL DEFAULT 0,
              due_date TEXT,
              priority TEXT,
              user_id INTEGER ,
              FOREIGN KEY (user_id) REFERENCES users (id)
          )''')
    conn.commit()
    conn.close()

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def get_id(self):
        return str(self.id)
    
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user_data = c.fetchone()
    conn.close()
    
    if user_data:
        return User(*user_data)
    return None



@app.route('/')
@login_required
def index():
    status = request.args.get('status')
    priority = request.args.get('priority')
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = 5 # Number of tasks shown per page

    query = "SELECT * FROM tasks WHERE user_id = ?"
    params = [current_user.id]

    if status == 'done':
        query += " AND done = 1"
    elif status == 'not_done':
        query += " AND done = 0"

    if priority and priority.lower() != 'all':
        query += " AND priority = ?"
        params.append(priority)

    if search:
        query += " AND content LIKE ?"
        params.append(f'%{search}%')

    query += " ORDER BY due_date IS NULL, due_date ASC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    conn = sqlite3.connect('todo.db')
    c = conn.cursor()
    c.execute(query, params)
    tasks = c.fetchall()

    count_query = "SELECT COUNT(*) FROM tasks WHERE user_id = ?"
    count_params = [current_user.id]

    if status == 'done':
        count_query += " AND done = 1"
    elif status == 'not_done':
        count_query += " AND done = 0"

    if priority:
        count_query += " AND priority = ?"
        count_params.append(priority)

    if search:
        count_query += " AND content LIKE ?"
        count_params.append(f'%{search}%')

    c.execute(count_query, count_params)
    total_tasks = c.fetchone()[0]

    conn.close()
    total_pages = (total_tasks + per_page - 1) // per_page

    return render_template('index.html', tasks=tasks, today=date.today(), page=page, total_pages=total_pages)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        conn = sqlite3.connect('todo.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            # Username already exists
            return "Username already exists"
        conn.close()
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        conn = sqlite3.connect('todo.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            login_user(User(*user))
            return redirect(url_for('index'))
        else:
            return "Invalid Credentials"
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/add', methods=['POST'])
@login_required
def add():
    content = request.form['content']
    due_date = request.form['due_date']
    priority = request.form['priority']


    if content:
        conn = sqlite3.connect('todo.db')
        c = conn.cursor()
        c.execute('INSERT INTO tasks (content, done, due_date, priority, user_id) VALUES (?, ?, ?, ?, ?)', (content, 0, due_date, priority, current_user.id))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()

    if request.method == 'POST':
        new_content = request.form['content']
        due_date = request.form['due_date']
        priority = request.form['priority']
        c.execute('UPDATE tasks SET content = ?, due_date = ?, priority = ? WHERE id = ? AND user_id = ?', 
                  (new_content, due_date, priority, task_id, current_user.id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    else:
        c.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, current_user.id))
        task = c.fetchone()
        conn.close()
        return render_template('edit.html', task=task)

@app.route('/delete/<int:task_id>')
@login_required
def delete(task_id):
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/complete/<int:task_id>')
def complete(task_id):
    conn = sqlite3.connect('todo.db')
    c = conn.cursor()
    c.execute('UPDATE tasks SET done = 1 WHERE id = ? AND user_id = ?', (task_id, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
