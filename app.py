from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_socketio import SocketIO, emit
import sqlite3
import os
import pandas as pd
from werkzeug.utils import secure_filename
from docx import Document
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
socketio = SocketIO(app)

UPLOAD_FOLDER = 'uploads'
EXPORT_FOLDER = 'export'
DB_FILE = 'comments.db'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    country TEXT,
                    paragraph_id INTEGER,
                    io_ref TEXT,
                    comment TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()

init_db()

# Global to hold parsed paragraphs
paragraphs = []

@app.route('/', methods=['GET', 'POST'])
def index():
    global paragraphs
    if request.method == 'POST':
        file = request.files['document']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            paragraphs = parse_docx(filepath)
            return redirect(url_for('index'))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM comments")
    comments = c.fetchall()
    conn.close()

    return render_template('index.html', paragraphs=paragraphs, comments=comments)

def parse_docx(path):
    doc = Document(path)
    paras = [para.text.strip() for para in doc.paragraphs if para.text.strip() != '']
    return paras

@app.route('/submit_comment', methods=['POST'])
def submit_comment():
    data = request.json
    country = data.get('country')
    paragraph_id = data.get('paragraph_id')
    io_ref = data.get('io_ref')
    comment_text = data.get('comment')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO comments (country, paragraph_id, io_ref, comment) VALUES (?, ?, ?, ?)",
              (country, paragraph_id, io_ref, comment_text))
    conn.commit()
    conn.close()

    socketio.emit('new_comment', data)
    return jsonify({'status': 'success'})

@app.route('/export_comments')
def export_comments():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM comments", conn)
    conn.close()

    # Add Paragraph Text
    paragraph_texts = []
    for idx in df['paragraph_id']:
        if 0 <= idx < len(paragraphs):
            paragraph_texts.append(paragraphs[idx])
        else:
            paragraph_texts.append("")

    df['paragraph_text'] = paragraph_texts

    output_path = os.path.join(EXPORT_FOLDER, 'comments_export.xlsx')
    df.to_excel(output_path, index=False)

    return send_file(output_path, as_attachment=True)

@app.route('/heatmap')
def heatmap():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM comments", conn)
    conn.close()

    if df.empty:
        return "No comments yet to display heatmap."

    comment_counts = df['paragraph_id'].value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(12, 3))

    sizes = comment_counts.values * 100  # Bubble sizes
    scatter = ax.scatter(
        comment_counts.index,
        [1] * len(comment_counts),  # Y-axis is constant
        s=sizes,
        alpha=0.6
    )

    ax.set_yticks([])
    ax.set_xlabel('Paragraph ID')
    ax.set_title('Comment Concentration Heatmap')
    ax.set_xlim(-1, max(comment_counts.index)+1)

    for idx, count in zip(comment_counts.index, comment_counts.values):
        ax.text(idx, 1.05, str(count), ha='center', va='bottom', fontsize=8)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()

    html = f'''
    <h1>Comment Heatmap</h1>
    <img src="data:image/png;base64,{encoded}">
    <p><a href="/">← Back to Main Page</a></p>
    '''
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
