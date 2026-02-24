from flask import Flask, render_template, request, redirect, session, url_for, abort, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection
from datetime import datetime, timedelta
import random
import pandas as pd
import io

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = "supersecretkey"


def admin_required():
    return 'user_id' in session and session.get('role') == 'admin'


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s,%s,%s,%s)",
            (request.form['name'], request.form['email'],
             generate_password_hash(request.form['password']),
             request.form['role'])
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (request.form['email'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        return "Invalid login"
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', role=session['role'])


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------------- ADMIN ----------------

@app.route('/admin/create_exam', methods=['GET', 'POST'])
def create_exam():
    if not admin_required():
        abort(403)

    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO exams (title, duration, total_marks, created_by)
            VALUES (%s,%s,%s,%s)
        """, (request.form['title'], request.form['duration'],
              request.form['total_marks'], session['user_id']))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_exams'))

    return render_template('admin_create_exam.html')


@app.route('/admin/exams')
def admin_exams():
    if not admin_required():
        abort(403)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM exams")
    exams = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin_exams.html', exams=exams)


@app.route('/admin/exam/<int:exam_id>/add_question', methods=['GET', 'POST'])
def add_question(exam_id):
    if not admin_required():
        abort(403)

    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO questions
            (exam_id, question_text, option1, option2, option3, option4, correct_option, marks)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (exam_id, request.form['question'], request.form['option1'],
              request.form['option2'], request.form['option3'],
              request.form['option4'], int(request.form['correct_option']),
              int(request.form['marks'])))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin_exams'))

    return render_template('admin_add_question.html', exam_id=exam_id)


# ---------------- STUDENT ----------------

@app.route('/student/exams')
def student_exams():
    if session.get('role') != 'student':
        abort(403)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM exams")
    exams = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('student_exams.html', exams=exams)


@app.route('/student/exam/<int:exam_id>')
def take_exam(exam_id):
    if session.get('role') != 'student':
        abort(403)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM results WHERE user_id=%s AND exam_id=%s",
                   (session['user_id'], exam_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return redirect(url_for('view_result', exam_id=exam_id))

    cursor.execute("SELECT * FROM exams WHERE id=%s", (exam_id,))
    exam = cursor.fetchone()

    cursor.execute("SELECT * FROM questions WHERE exam_id=%s", (exam_id,))
    raw_questions = cursor.fetchall()

    questions = []
    for q in raw_questions:
        options = [
            {"text": q['option1'], "is_correct": q['correct_option'] == 1},
            {"text": q['option2'], "is_correct": q['correct_option'] == 2},
            {"text": q['option3'], "is_correct": q['correct_option'] == 3},
            {"text": q['option4'], "is_correct": q['correct_option'] == 4},
        ]

        random.shuffle(options)

        for idx, opt in enumerate(options, start=1):
            if opt['is_correct']:
                q['correct_option'] = idx

        q['shuffled_options'] = options
        questions.append(q)

    random.shuffle(questions)

    cursor.close()
    conn.close()

    session['exam_start'] = datetime.now().isoformat()
    return render_template('take_exam.html', exam=exam, questions=questions)


@app.route('/student/submit_exam/<int:exam_id>', methods=['POST'])
def submit_exam(exam_id):
    if session.get('role') != 'student':
        abort(403)

    if 'exam_start' not in session:
        return redirect(url_for('view_result', exam_id=exam_id))

    start_time = datetime.fromisoformat(session['exam_start'])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT duration FROM exams WHERE id=%s", (exam_id,))
    duration = cursor.fetchone()['duration']
    end_time = start_time + timedelta(minutes=duration)

    if datetime.now() > end_time:
        return redirect(url_for('view_result', exam_id=exam_id))

    cursor.execute("SELECT * FROM questions WHERE exam_id=%s", (exam_id,))
    questions = cursor.fetchall()

    score = 0
    for q in questions:
        selected = request.form.get(f"q{q['id']}")
        if selected and int(selected) == q['correct_option']:
            score += q['marks']

    cursor2 = conn.cursor()
    cursor2.execute(
        "INSERT INTO results (user_id, exam_id, score) VALUES (%s,%s,%s)",
        (session['user_id'], exam_id, score)
    )
    conn.commit()

    cursor.close()
    cursor2.close()
    conn.close()

    session.pop('exam_start', None)
    return redirect(url_for('view_result', exam_id=exam_id))


@app.route('/student/result/<int:exam_id>')
def view_result(exam_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT r.score, e.total_marks 
        FROM results r 
        JOIN exams e ON r.exam_id = e.id 
        WHERE r.user_id=%s AND r.exam_id=%s
        ORDER BY r.id DESC LIMIT 1
    """, (session['user_id'], exam_id))

    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        return "Result not found."

    percentage = (result['score'] / result['total_marks']) * 100

    return render_template('student_result.html',
                           score=result['score'],
                           total=result['total_marks'],
                           percentage=percentage)


# ---------------- ADMIN ANALYTICS ----------------

@app.route('/admin/results')
def admin_results():
    if not admin_required():
        abort(403)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            e.id, e.title,
            COUNT(r.id) AS attempts,
            MAX(r.score) AS highest,
            AVG(r.score) AS average,
            MIN(r.score) AS lowest
        FROM exams e
        LEFT JOIN results r ON e.id = r.exam_id
        GROUP BY e.id
    """)
    exam_stats = cursor.fetchall()

    cursor.execute("""
        SELECT 
            u.name AS student_name,
            e.title AS exam_title,
            r.score,
            e.total_marks,
            r.submitted_at
        FROM results r
        JOIN users u ON r.user_id = u.id
        JOIN exams e ON r.exam_id = e.id
        ORDER BY r.submitted_at DESC
    """)
    detailed_results = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_results.html',
                           exam_stats=exam_stats,
                           detailed_results=detailed_results)


# ---------------- EXCEL EXPORT ----------------

@app.route('/admin/export_exam/<int:exam_id>')
def export_exam_excel(exam_id):
    if not admin_required():
        abort(403)

    conn = get_db_connection()

    query = """
        SELECT 
            u.name AS Student,
            u.email AS Email,
            e.title AS Exam,
            r.score AS Score,
            e.total_marks AS Total,
            ROUND((r.score / e.total_marks) * 100, 2) AS Percentage,
            r.submitted_at AS SubmittedAt
        FROM results r
        JOIN users u ON r.user_id = u.id
        JOIN exams e ON r.exam_id = e.id
        WHERE e.id = %s
    """

    df = pd.read_sql(query, conn, params=(exam_id,))
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Results')

    output.seek(0)

    return send_file(output,
                     download_name=f"exam_{exam_id}_results.xlsx",
                     as_attachment=True)


# ---------------- PDF EXPORT ----------------

@app.route('/admin/export_exam_pdf/<int:exam_id>')
def export_exam_pdf(exam_id):
    if not admin_required():
        abort(403)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            u.name AS student,
            u.email AS email,
            r.score AS score,
            e.total_marks AS total,
            ROUND((r.score / e.total_marks) * 100, 2) AS percentage
        FROM results r
        JOIN users u ON r.user_id = u.id
        JOIN exams e ON r.exam_id = e.id
        WHERE e.id = %s
    """, (exam_id,))
    rows = cursor.fetchall()

    cursor.execute("SELECT title FROM exams WHERE id=%s", (exam_id,))
    exam_title = cursor.fetchone()['title']

    cursor.close()
    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = []

    title = Paragraph(f"<b>{exam_title} - Result Report</b>", styles['Title'])
    elements.append(title)

    data = [["Student", "Email", "Score", "Total", "Percentage"]]
    for r in rows:
        data.append([r['student'], r['email'], r['score'],
                     r['total'], f"{r['percentage']}%"])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (2, 1), (-1, -1), 'CENTER')
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)

    return send_file(buffer,
                     as_attachment=True,
                     download_name=f"exam_{exam_id}_results.pdf",
                     mimetype='application/pdf')

@app.route('/student/history')
def student_history():
    if session.get('role') != 'student':
        abort(403)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.title, r.score, e.total_marks, r.submitted_at
        FROM results r
        JOIN exams e ON r.exam_id = e.id
        WHERE r.user_id = %s
        ORDER BY r.submitted_at DESC
    """, (session['user_id'],))

    history = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('student_history.html', history=history)


if __name__ == "__main__":
    app.run(debug=True)
