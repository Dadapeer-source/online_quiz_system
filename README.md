# 🧠 Online Examination System (Flask + MySQL)

A full-stack web-based Online Examination System built using Flask and MySQL.  
This platform allows admins to create exams and students to take timed tests with automatic evaluation and result tracking.

---

## 🚀 Features

### 🔐 Authentication
- User Registration & Login
- Role-based access (Admin / Student)
- Secure password hashing

### 👨‍🏫 Admin Panel
- Create exams with duration and total marks
- Add multiple-choice questions
- View all exams
- View student results and analytics
- Export results (Excel & PDF)

### 🎓 Student Panel
- View available exams
- Attempt exams with timer
- Automatic scoring
- View results instantly
- Performance history tracking
- Retake restriction (one attempt per exam)

### ⏱️ Exam System
- Timer-based exam submission
- Auto-submit when time ends
- Randomized question options (anti-cheating basic level)

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Database:** MySQL
- **Frontend:** HTML, CSS, JavaScript
- **Libraries:**
  - `mysql-connector-python`
  - `werkzeug.security`
  - `reportlab` (PDF export)
  - `pandas` (Excel export)

---

## 📁 Project Structure
online_quiz_system/
│
├── app.py
├── db.py
├── config.py
├── requirements.txt
│
├── templates/
│ ├── login.html
│ ├── register.html
│ ├── dashboard.html
│ ├── admin_create_exam.html
│ ├── admin_add_question.html
│ ├── admin_exams.html
│ ├── admin_results.html
│ ├── student_exams.html
│ ├── take_exam.html
│ ├── student_result.html
│ └── student_history.html
│└── static/ (optional for CSS/JS)


---

## ⚙️ Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/Dadapeer-source/online_quiz_system.git
cd online-exam-system


2. Create Virtual Environment
python -m venv venv
venv\Scripts\activate

3. Install Dependencies
pip install -r requirements.txt

4. Setup MySQL Database
CREATE DATABASE quiz_system;
USE quiz_system;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password TEXT,
    role ENUM('admin','student')
);

CREATE TABLE exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    duration INT,
    total_marks INT,
    created_by INT
);

CREATE TABLE questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT,
    question_text TEXT,
    option1 TEXT,
    option2 TEXT,
    option3 TEXT,
    option4 TEXT,
    correct_option INT,
    marks INT
);

CREATE TABLE results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    exam_id INT,
    score INT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


5. Configure Database
host="localhost"
user="root"
password="your_password"
database="quiz_system"

6. Run Application
python app.py

### ▶️ Run the App

After starting the server, open your browser and go to:

http://localhost:5000/