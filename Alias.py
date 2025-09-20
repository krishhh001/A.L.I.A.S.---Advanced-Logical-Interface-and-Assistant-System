import os
import subprocess
import pyautogui
import speech_recognition as sr
import pyttsx3
import webbrowser
import mysql.connector
import datetime
import time
from urllib.parse import quote
import sympy as sp
import re
import traceback
import google.generativeai as genai
import requests

from dotenv import load_dotenv #changed

load_dotenv() #changed

############################################################################################
import os
import requests
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
USER_COUNTRY = os.getenv("NEWS_COUNTRY", "us")

if not GEMINI_API_KEY:
    raise ValueError(
        "❌ Gemini API key is missing!\n"
        "Please create a .env file in your project folder with:\n"
        "GEMINI_API_KEY=your_actual_key_here"
    )

def gemini_chat(prompt, max_retries: int = 3, timeout: int = 15):
    """Send a prompt to Gemini API with retries and return the response text or a friendly fallback."""
    if not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "":
        return "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env."
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1000}
    }
    backoff = 1.0
    last_error = None
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code >= 500:
                raise requests.exceptions.HTTPError(f"{resp.status_code} {resp.reason}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            last_error = e
            time.sleep(backoff)
            backoff *= 2
            continue
        except Exception as e:
            last_error = e
            break
    return f"Service is temporarily unavailable. Please try again in a moment. ({last_error})"

###############################################################################################################

# ==== CONFIGURATION ====
# Set your Gemini API key here, or use an environment variable for better security
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Use only the environment variable; no hardcoded default

# No genai.configure for older SDKs
# ==== TEXT TO SPEECH ====
engine = pyttsx3.init()
engine.setProperty('rate', 150)
voices = engine.getProperty('voices')
# Use the first available voice instead of hardcoding index 2
if voices:
    engine.setProperty('voice', voices[0].id)

# Define speak before any function uses it
import threading
_speaking_thread = None

def speak(text):
    print(f"ALIAS: {text}")
    try:
        global _speaking_thread
        # Stop any existing speech first
        if _speaking_thread and _speaking_thread.is_alive():
            engine.stop()
        
        def _speak_worker():
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                print("[TTS ERROR]", e)
        
        _speaking_thread = threading.Thread(target=_speak_worker, daemon=True)
        _speaking_thread.start()
    except Exception as e:
        print("[TTS ERROR]", e)

def stop_speaking():
    """Immediately stop any ongoing TTS playback."""
    try:
        engine.stop()
        # Clear any queued speech
        engine.stop()
    except Exception as e:
        print("[TTS STOP ERROR]", e)

# ==== NEW IMPORTS FOR PDF/FILES/CAMERA/EMAIL ====
import tempfile
import docx2txt
from PyPDF2 import PdfReader
import cv2
import base64
import imaplib
import smtplib
import ssl
from email.message import EmailMessage

# Email configuration from environment
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# ==== UTILITIES: PDF EXPORT AND DOCUMENT ANALYSIS ====
def export_text_to_pdf(text, output_path=None):
    """Export given text to a simple PDF file and return file path."""
    try:
        # Lazy import to avoid linter/module issues until installed
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        if not output_path:
            fd, tmp_path = tempfile.mkstemp(prefix="friday_", suffix=".pdf")
            os.close(fd)
            output_path = tmp_path
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        margin = 0.75 * inch
        y = height - margin
        max_width = width - 2 * margin
        # Simple word-wrap
        words = text.split()
        line = ""
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 11) > max_width:
                c.setFont("Helvetica", 11)
                c.drawString(margin, y, line)
                y -= 14
                if y < margin:
                    c.showPage()
                    y = height - margin
                line = word
            else:
                line = test
        if line:
            c.setFont("Helvetica", 11)
            c.drawString(margin, y, line)
        c.save()
        speak(f"Saved PDF to {output_path}")
        return output_path
    except Exception as e:
        speak("Failed to export PDF.")
        print("[PDF Export Error]", e)
        return None


def read_text_from_file(file_path):
    """Read text from TXT, PDF, DOCX. Return extracted text or None."""
    try:
        lower = file_path.lower()
        if lower.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        if lower.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            texts = []
            for page in reader.pages:
                try:
                    texts.append(page.extract_text() or "")
                except Exception:
                    pass
            return "\n".join(texts).strip()
        if lower.endswith(".docx"):
            import docx2txt
            return docx2txt.process(file_path) or ""
        return None
    except Exception as e:
        speak("Failed to read the document.")
        print("[Read File Error]", e)
        return None


def analyze_document(file_path):
    """Extract text and run Gemini summary/analysis. Return summary string."""
    try:
        text = read_text_from_file(file_path)
        if not text:
            return "Could not extract text from document."
        prompt = (
            "Summarize and analyze the following document. Extract key points, action items, and any entities.\n\n" 
            + text[:12000]
        )
        summary = gemini_chat(prompt)
        return summary or "No analysis produced."
    except Exception as e:
        print("[Analyze Document Error]", e)
        return "Failed to analyze document."


# ==== CAMERA HELPERS ====
def capture_camera_image(output_path=None):
    """Capture a single image from default camera and return path."""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        if not output_path:
            fd, tmp_path = tempfile.mkstemp(prefix="friday_cam_", suffix=".png")
            os.close(fd)
            output_path = tmp_path
        cv2.imwrite(output_path, frame)
        return output_path
    except Exception as e:
        print("[Camera Capture Error]", e)
        return None


def identify_product_from_image(image_path):
    """Identify product by sending image to Gemini Vision using inline base64 data."""
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": "You are a visual assistant. Identify the product in this photo. Describe brand, type, and notable features in 2-4 lines."},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256}
        }
        resp = requests.post(url, headers=headers, json=data, timeout=20)
        resp.raise_for_status()
        result = resp.json()
        text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return text or "I couldn't confidently identify the product."
    except Exception as e:
        print("[Product ID Error]", e)
        return "Failed to identify the product."

# ==== EMAIL HELPERS ====

def email_read_latest(count=5):
    """Read latest count emails (subject + from). Returns a string summary."""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD in .env."
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("inbox")
        typ, data = mail.search(None, 'ALL')
        ids = data[0].split()
        ids = ids[-count:]
        lines = []
        for num in reversed(ids):
            typ, msg_data = mail.fetch(num, '(RFC822)')
            if typ != 'OK':
                continue
            import email
            msg = email.message_from_bytes(msg_data[0][1])
            subject = msg.get('Subject', '(No Subject)')
            from_ = msg.get('From', '(Unknown)')
            lines.append(f"From: {from_} | Subject: {subject}")
        mail.close()
        mail.logout()
        return "\n".join(lines) if lines else "No emails found."
    except Exception as e:
        print("[Email Read Error]", e)
        return "Failed to read emails."


def email_send(to_address, subject, body):
    """Send an email."""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        return "Email not configured. Set EMAIL_ADDRESS and EMAIL_PASSWORD in .env."
    try:
        msg = EmailMessage()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.set_content(body)
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return "Email sent successfully."
    except Exception as e:
        print("[Email Send Error]", e)
        return "Failed to send email."

# ==== EYE SCAN SECURITY GATE ====

def eye_scan_gate(timeout_seconds=10):
    """Configurable identity check using webcam. Modes via ALIAS_IDENTITY_MODE:
    - off: skip check, always pass
    - lenient (default): pass if a face is detected or on timeout
    - strict: require eyes detected within timeout
    Returns True if access granted.
    """
    try:
        mode = os.getenv("ALIAS_IDENTITY_MODE", "lenient").strip().lower()
        if mode == "off":
            speak("Identity check skipped.")
            return True

        import cv2
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            speak("Camera not available. Skipping identity check.")
            return True

        import time
        start = time.time()
        speak("Security check: Please look at the camera.")
        passed = False
        while time.time() - start < timeout_seconds:
            ret, frame = cap.read()
            if not ret:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.2, 5)
            if len(faces) > 0 and mode == "lenient":
                passed = True
                break
            for (x, y, w, h) in faces:
                roi_gray = gray[y:y+h, x:x+w]
                eyes = eye_cascade.detectMultiScale(roi_gray)
                if len(eyes) >= 1:
                    passed = True
                    break
            if passed:
                break
        cap.release()

        if passed:
            speak("Identity check passed.")
            return True

        # Timeout fallback by mode
        if mode == "lenient":
            speak("Identity check timed out. Allowing access.")
            return True
        else:
            speak("Identity check failed.")
            return False
    except Exception as e:
        print("[Eye Scan Error]", e)
        # Fail-open to avoid blocking usage
        return True

# ==== LISTEN COMMAND ====
def listen_command():
    recognizer = sr.Recognizer()
    try:
        print("🎤 Attempting to access microphone...")
        with sr.Microphone() as source:
            print("🎤 Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            command = recognizer.recognize_google(audio)
            print(f"🗣 You said: {command}")
            return str(command).lower()
    except sr.UnknownValueError:
        print("Could not understand audio")
        speak("Couldn't hear you. Please type your command:")
        command = input("Type here: ")
        return command.lower()
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        speak("Couldn't hear you. Please type your command:")
        command = input("Type here: ")
        return command.lower()
    except Exception as e:
        print(f"Microphone error: {e}")
        speak("Couldn't hear you. Please type your command:")
        command = input("Type here: ")
        return command.lower()

# ==== SYSTEM TASK CONTROL ====
def execute_command(command):
    try:
        if "open" in command:
            app_name = command.replace("open", "").strip()
            speak(f"Opening {app_name}")
            pyautogui.hotkey('ctrl', 'esc')  # Open Start menu
            pyautogui.typewrite(app_name)
            pyautogui.press('enter')
        elif "close" in command:
            app_name = command.replace("close", "").strip()
            if "chrome" in app_name:
                speak("Closing Chrome")
                os.system("taskkill /f /im chrome.exe")
            elif "notepad" in app_name:
                speak("Closing Notepad")
                os.system("taskkill /f /im notepad.exe")
            else:
                # Try to close any app by guessing its process name
                exe_name = app_name.replace(" ", "") + ".exe"
                speak(f"Trying to close {app_name} (process: {exe_name})")
                print(f"Trying to close process: {exe_name}")
                result = os.system(f"taskkill /f /im {exe_name}")
                if result != 0:
                    speak(f"Could not close {app_name}. The process {exe_name} may not exist or is named differently.")
        elif "volume up" in command:
            pyautogui.press("volumeup")
            speak("Volume up")
        elif "volume down" in command:
            pyautogui.press("volumedown")
            speak("Volume down")
        elif "mute" in command:
            pyautogui.press("volumemute")
            speak("Volume muted")
    except Exception as e:
        speak("System command failed.")
        print("[System Error]", e)

# ==== MATH SOLVER ====
def solve_math(command):
    try:
        # Remove trigger words and extra spaces
        expression = command.lower().replace("solve", "").replace("calculate", "").strip()
        # Try to parse and evaluate with sympy
        try:
            # Replace common words and symbols
            expression = expression.replace("x", "*").replace("^", "**")
            # Remove 'what is', 'the value of', etc.
            for phrase in ["what is ", "the value of ", "?", "equals", "=", "find "]:
                expression = expression.replace(phrase, "")
            result = sp.sympify(expression)
            speak(f"The answer is {result}")
        except Exception:
            # Fallback: Use OpenAI to solve if sympy fails
            speak("Let me try to solve it using AI.")
            answer = gemini_chat(f"Solve this math problem: {command}")
            answer = answer.strip() if answer else ""
            speak(f"AI says: {answer}")
    except Exception as e:
        speak("Couldn't solve the math problem.")
        print("[Math Error]", e)

# ==== CODE GENERATOR ====
def generate_code(command):
    prompt = f"Write a Python program to {command.replace('code', '').replace('program', '').strip()}"
    try:
        speak("Generating code, please wait.")
        code = gemini_chat(prompt)
        code = code.strip() if code else ""
        speak("Here is the code:")
        print("\n" + code)
    except Exception as e:
        speak("Code generation failed.")
        print("[Gemini Code Error]", e)

# ==== NEWS HELPERS ====

def summarize_text_bullets(text, bullets=5):
    try:
        prompt = f"Summarize the following news items into {bullets} concise bullet points:\n\n{text[:12000]}"
        return gemini_chat(prompt) or text
    except Exception:
        return text


def fetch_news_newsapi(category: str = "general", country: str = None, page_size: int = 8):
    if not NEWSAPI_KEY:
        return None
    try:
        country = country or USER_COUNTRY
        url = f"https://newsapi.org/v2/top-headlines?country={country}&category={category}&pageSize={page_size}&apiKey={NEWSAPI_KEY}"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        articles = data.get("articles", [])
        lines = []
        for a in articles:
            title = a.get("title") or "(no title)"
            source = (a.get("source") or {}).get("name") or ""
            lines.append(f"- {title} ({source})")
        return "\n".join(lines)
    except Exception as e:
        print("[NewsAPI Error]", e)
        return None


def fetch_news_rss(topic: str = "world", page_size: int = 8):
    try:
        import feedparser
        feeds = {
            "world": "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
            "national": f"https://news.google.com/rss/headlines/section/geo/{USER_COUNTRY.upper()}?hl=en-US&gl=US&ceid=US:en",
            "business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en"
        }
        url = feeds.get(topic, feeds["world"])
        d = feedparser.parse(url)
        entries = d.entries[:page_size]
        lines = [f"- {e.title}" for e in entries if hasattr(e, 'title')]
        return "\n".join(lines)
    except Exception as e:
        print("[RSS Error]", e)
        return None


def get_news_summary(scope: str = "international") -> str:
    # scope: "national" or "international"
    if scope == "national":
        text = fetch_news_newsapi(category="general", country=USER_COUNTRY) or fetch_news_rss("national")
    else:
        text = fetch_news_newsapi(category="general", country="us") or fetch_news_rss("world")
    if not text:
        return "Couldn't fetch news right now."
    return summarize_text_bullets(text, bullets=7)

# ==== EMAIL COMMAND HANDLERS ====

def handle_email_command(command: str) -> str:
    lower = command.lower()
    try:
        if "read" in lower or "inbox" in lower:
            summary = email_read_latest(5)
            return summary
        if "send" in lower:
            # naive parse: "send email to x about y: body..."
            to_match = re.search(r"to\s+([^\s]+@[^\s]+)", command, re.IGNORECASE)
            subject_match = re.search(r"subject\s*[:\-]\s*(.+?)\s*body\s*[:\-]", command, re.IGNORECASE)
            body_match = re.search(r"body\s*[:\-]\s*(.+)$", command, re.IGNORECASE | re.DOTALL)
            to_addr = to_match.group(1) if to_match else None
            subject = subject_match.group(1).strip() if subject_match else "(No Subject)"
            body = body_match.group(1).strip() if body_match else ""
            if not to_addr:
                return "Please specify recipient email like: send email to user@example.com subject: Hello body: Hi"
            return email_send(to_addr, subject, body)
        return "Email command not understood. Try: 'read emails' or 'send email to ...'"
    except Exception as e:
        print("[Handle Email Error]", e)
        return "Failed to process email command."

# ==== SQLITE DATABASE FOR CHAT HISTORY ====
import sqlite3
import json
from datetime import datetime

# SQLite database for chat history and memory
DB_PATH = "alias_chat_history.db"

def init_chat_database():
    """Initialize SQLite database for chat history and memory."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Chat history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                command_type TEXT,
                session_id TEXT
            )
        ''')
        
        # Query memory table for learning patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                success_rate REAL DEFAULT 1.0
            )
        ''')
        
        # User preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Chat database initialized successfully.")
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

def save_chat_message(user_msg: str, assistant_msg: str, command_type: str = "general", session_id: str = "default"):
    """Save chat message to database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chat_history (user_message, assistant_response, command_type, session_id)
            VALUES (?, ?, ?, ?)
        ''', (user_msg, assistant_msg, command_type, session_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving chat: {e}")
        return False

def get_recent_chat_history(limit: int = 10, session_id: str = "default"):
    """Get recent chat history for context."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_message, assistant_response, command_type, timestamp
            FROM chat_history 
            WHERE session_id = ?
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (session_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

def update_query_memory(query: str, response: str, success: bool = True):
    """Update query memory for learning patterns."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if query exists
        cursor.execute('SELECT id, frequency, success_rate FROM query_memory WHERE query = ?', (query,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing query
            query_id, freq, success_rate = existing
            new_freq = freq + 1
            new_success_rate = ((success_rate * freq) + (1.0 if success else 0.0)) / new_freq
            
            cursor.execute('''
                UPDATE query_memory 
                SET frequency = ?, success_rate = ?, last_used = CURRENT_TIMESTAMP, response = ?
                WHERE id = ?
            ''', (new_freq, new_success_rate, response, query_id))
        else:
            # Insert new query
            cursor.execute('''
                INSERT INTO query_memory (query, response, success_rate)
                VALUES (?, ?, ?)
            ''', (query, response, 1.0 if success else 0.0))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating query memory: {e}")
        return False

def get_similar_queries(query: str, limit: int = 3):
    """Find similar queries from memory."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Simple similarity search (can be enhanced with fuzzy matching)
        cursor.execute('''
            SELECT query, response, frequency, success_rate
            FROM query_memory 
            WHERE query LIKE ? OR query LIKE ? OR query LIKE ?
            ORDER BY frequency DESC, success_rate DESC
            LIMIT ?
        ''', (f"%{query}%", f"%{query.split()[0]}%", f"%{query.split()[-1]}%", limit))
        
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"Error getting similar queries: {e}")
        return []

def get_chat_statistics():
    """Get chat statistics."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total messages
        cursor.execute('SELECT COUNT(*) FROM chat_history')
        total_messages = cursor.fetchone()[0]
        
        # Most common command types
        cursor.execute('''
            SELECT command_type, COUNT(*) as count 
            FROM chat_history 
            GROUP BY command_type 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        command_stats = cursor.fetchall()
        
        # Recent activity
        cursor.execute('''
            SELECT COUNT(*) FROM chat_history 
            WHERE timestamp > datetime('now', '-1 day')
        ''')
        recent_activity = cursor.fetchone()[0]
        
        conn.close()
        return {
            'total_messages': total_messages,
            'command_stats': command_stats,
            'recent_activity': recent_activity
        }
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return {}

# ==== MYSQL SUPPORT ====
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_mysql_password",
    "database": "your_database_name"
}

# Store the current database name globally
current_database = MYSQL_CONFIG["database"]

def connect_mysql(database=None):
    try:
        config = MYSQL_CONFIG.copy()
        if database:
            config["database"] = database
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        speak(f"Database error: {err}")
        return None

# New: Create database and table from user command
def create_database_from_command(command):
    try:
        # Extract the subject (e.g., students, employees)
        subject = command.lower().replace("create a database for", "").replace("create database for", "").replace("create a database", "").replace("create database", "").strip()
        if not subject:
            speak("Please specify what the database is for, like students or employees.")
            return
        db_name = f"friday_{subject.replace(' ', '_')}"
        speak(f"Creating a database for {subject}.")
        # Use OpenAI to generate a table schema
        prompt = f"Generate a MySQL CREATE TABLE statement for a table called {subject} with appropriate columns. Only output the SQL statement."
        sql = gemini_chat(prompt)
        print("[DEBUG] Generated SQL:", sql)
        if not sql:
            speak("Failed to get table schema from AI.")
            print("[DEBUG] No SQL returned from Gemini.")
            return
        sql = sql.strip()
        match = re.search(r'CREATE TABLE (\w+)', sql, re.IGNORECASE)
        table_name = match.group(1) if match else subject
        # Connect to MySQL (no database yet)
        conn = connect_mysql(database=None)
        if not conn:
            speak("Could not connect to MySQL server.")
            print("[DEBUG] MySQL connection failed.")
            return
        cursor = conn.cursor() if conn else None
        if not cursor:
            speak("Could not get MySQL cursor.")
            conn.close()
            print("[DEBUG] MySQL cursor failed.")
            return
        # Create database
        try:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        except Exception as e:
            speak("Failed to create database.")
            print("[DEBUG] Exception during CREATE DATABASE:", e)
            traceback.print_exc()
            cursor.close()
            conn.close()
            return
        cursor.close()
        conn.close()
        # Now connect to the new database and create the table
        conn2 = connect_mysql(database=db_name)
        if not conn2:
            speak(f"Could not connect to the new database {db_name}.")
            print(f"[DEBUG] Connection to new database {db_name} failed.")
            return
        cursor2 = conn2.cursor()
        try:
            cursor2.execute(sql)
            conn2.commit()
        except Exception as e:
            speak("Failed to create table. Check the SQL syntax.")
            print("[DEBUG] Exception during CREATE TABLE:", e)
            print("[DEBUG] SQL attempted:", sql)
            traceback.print_exc()
            cursor2.close()
            conn2.close()
            return
        cursor2.close()
        conn2.close()
        global current_database
        current_database = db_name
        speak(f"Database '{db_name}' and table '{table_name}' created. Now using this database.")
    except Exception as e:
        speak("Failed to create database or table.")
        print("[Create DB Error]", e)
        traceback.print_exc()

def handle_mysql_query(command):
    try:
        conn = connect_mysql(database=current_database)
        if not conn:
            return
        cursor = conn.cursor()
        sql = command.replace("run query", "").replace("mysql", "").strip()
        cursor.execute(sql)
        if sql.lower().startswith("select"):
            results = cursor.fetchall()
            if results:
                for row in results[:5]:
                    print(row)
                    speak(str(row))
            else:
                speak("Query ran successfully. No results.")
        else:
            conn.commit()
            speak("Query executed successfully.")
        cursor.close()
        conn.close()
    except Exception as e:
        speak("Failed to run SQL command.")
        print("[MySQL Error]", e)

def nl_to_sql(command):
    speak("Translating your request into SQL...")
    try:
        table_info = f"Assume the database has tables relevant to the current context."
        prompt = f"{table_info} Convert the following request to SQL: {command}"
        sql = gemini_chat(prompt)
        sql = sql.strip() if sql else ""
        print("SQL Generated:", sql)
        handle_mysql_query("run query " + sql)
    except Exception as e:
        speak("Couldn't translate to SQL.")
        print("[NL to SQL Error]", e)

# ==== WEB SEARCH / AI QUERY ====
def handle_query(command):
    try:
        if "search" in command:
            query = command.replace("search", "").strip().replace(" ", "+")
            speak(f"Searching for {query}")
            url = f"https://www.google.com/search?q={quote(query)}"
            chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            if os.path.exists(chrome_path):
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
                webbrowser.get('chrome').open_new_tab(url)
            else:
                webbrowser.open_new_tab(url)
        else:
            speak("Let me find the answer for you.")
            try:
                answer = gemini_chat(command)
                answer = answer.strip() if answer else ""
                speak(answer)
                print("Gemini Answer:", answer)
            except Exception as e:
                speak("Something went wrong with Gemini.")
                print("[Gemini Error]", e)
                import traceback
                traceback.print_exc()
    except Exception as e:
        speak("Something went wrong with Gemini.")
        print("[Gemini Error]", e)
        import traceback
        traceback.print_exc()

# ==== STARTUP ANIMATION ====
def show_startup_animation():
    """No-op placeholder; PyQt6 UI is the primary interface now."""
    print("Startup animation skipped (PyQt6 UI is primary).")
    return True

# ==== PERSISTENT INTERFACE ====
def show_persistent_interface():
    """Show the Friday AI PyQt6 interface."""
    try:
        from qt_friday_ui import show_friday_qt
        print("Launching Friday AI PyQt6 interface...")
        show_friday_qt()
        return True
    except Exception as e:
        print(f"PyQt6 UI error: {e}")
        return False

# ==== MAIN LOOP ====
def main():
    print("Starting ALIAS voice assistant...")
    # Eye scan before interface
    if not eye_scan_gate():
        print("Access denied by eye scan.")
        return
    
    # Try to show persistent interface first
    if not show_persistent_interface():
        # Fallback to startup animation + CLI
        show_startup_animation()
        
        try:
            speak("Hello, I am ALIAS. How can I assist you?")
            print("ALIAS is ready to listen!")
            while True:
                command = listen_command()
                if not command:
                    continue
                elif "exit" in command or "stop" in command:
                    speak("Goodbye!")
                    break
                elif command.startswith("create a database") or command.startswith("create database"):
                    create_database_from_command(command)
                elif any(word in command for word in ["open", "close", "volume"]):
                    execute_command(command)
                elif "solve" in command or "calculate" in command or any(char.isdigit() for char in command):
                    solve_math(command)
                elif "code" in command or "program" in command:
                    generate_code(command)
                elif "run query" in command or "mysql" in command:
                    handle_mysql_query(command)
                elif "database" in command or "sql" in command:
                    nl_to_sql(command)
                elif "email" in command:
                    resp = handle_email_command(command)
                    speak(resp)
                    print(resp)
                elif "news" in command:
                    scope = "national" if ("national" in command or "india" in command or "local" in command) else "international"
                    summary = get_news_summary(scope)
                    speak(summary)
                    print(summary)
                else:
                    handle_query(command)
        except Exception as e:
            print(f"Error in main loop: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()

