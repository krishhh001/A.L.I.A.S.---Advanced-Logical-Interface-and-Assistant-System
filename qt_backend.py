import threading
from typing import Callable, Optional
import webbrowser
from urllib.parse import quote
import os

# Global TTS switch (on by default)
TTS_ENABLED: bool = True

def set_tts_enabled(enabled: bool) -> None:
    global TTS_ENABLED
    TTS_ENABLED = enabled

class FridayBackend:
    """Consolidated backend that handles all Friday AI functionality."""

    def __init__(self):
        self._lock = threading.Lock()
        # Import all Friday functions
        self._import_friday_functions()
        # Initialize chat database
        self.init_chat_database()

    def _import_friday_functions(self):
        """Import all necessary functions from friday.py"""
        try:
            from friday import (
                gemini_chat,
                analyze_document,
                execute_command,
                solve_math,
                generate_code,
                handle_mysql_query,
                nl_to_sql,
                handle_email_command,
                get_news_summary,
                speak,
                stop_speaking,
                save_chat_message,
                get_recent_chat_history,
                update_query_memory,
                get_similar_queries,
                init_chat_database,
            )
            self.gemini_chat = gemini_chat
            self.analyze_document = analyze_document
            self.execute_command = execute_command
            self.solve_math = solve_math
            self.generate_code = generate_code
            self.handle_mysql_query = handle_mysql_query
            self.nl_to_sql = nl_to_sql
            self.handle_email_command = handle_email_command
            self.get_news_summary = get_news_summary
            self.speak = speak
            self.stop_speaking = stop_speaking
            self.save_chat_message = save_chat_message
            self.get_recent_chat_history = get_recent_chat_history
            self.update_query_memory = update_query_memory
            self.get_similar_queries = get_similar_queries
            self.init_chat_database = init_chat_database
        except Exception as e:
            print(f"Warning: Could not import some Friday functions: {e}")
            # Fallback functions
            self.gemini_chat = lambda x: f"(backend unavailable) {x}"
            self.analyze_document = lambda x: f"(backend unavailable) Could not analyze: {x}"
            self.execute_command = lambda x: None
            self.solve_math = lambda x: None
            self.generate_code = lambda x: None
            self.handle_mysql_query = lambda x: ""
            self.nl_to_sql = lambda x: None
            self.handle_email_command = lambda x: ""
            self.get_news_summary = lambda x: ""
            self.speak = lambda x: None
            self.stop_speaking = lambda: None
            self.save_chat_message = lambda a, b, c="general", d="default": None
            self.get_recent_chat_history = lambda a=10, b="default": []
            self.update_query_memory = lambda a, b, c=True: None
            self.get_similar_queries = lambda a, b=3: []
            self.init_chat_database = lambda: None

    def _handle_web_commands(self, lower: str) -> str:
        """Handle web browser commands"""
        chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        if os.path.exists(chrome_path):
            webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
        
        try:
            if lower.startswith("open youtube"):
                query = lower.replace("open youtube", "").strip()
                url = "https://www.youtube.com/"
                if query:
                    url = f"https://www.youtube.com/results?search_query={quote(query)}"
                webbrowser.get('chrome').open_new_tab(url) if os.path.exists(chrome_path) else webbrowser.open_new_tab(url)
                return f"Opened YouTube{': ' + query if query else ''}"
            
            elif lower.startswith("open chrome and search") or lower.startswith("open chrome & search"):
                q = lower.split("search", 1)[1].strip() if "search" in lower else ""
                url = f"https://www.google.com/search?q={quote(q)}" if q else "https://www.google.com"
                webbrowser.get('chrome').open_new_tab(url) if os.path.exists(chrome_path) else webbrowser.open_new_tab(url)
                return f"Opened Chrome search: {q}" if q else "Opened Chrome"
            
            elif lower.startswith("open chrome") and "search" in lower:
                q = lower.split("search", 1)[1].strip()
                url = f"https://www.google.com/search?q={quote(q)}"
                webbrowser.get('chrome').open_new_tab(url) if os.path.exists(chrome_path) else webbrowser.open_new_tab(url)
                return f"Opened Chrome search: {q}"
            
            elif lower.startswith("open chrome") and "search" not in lower:
                webbrowser.get('chrome').open_new_tab("https://www.google.com") if os.path.exists(chrome_path) else webbrowser.open_new_tab("https://www.google.com")
                return "Opened Chrome"
        except Exception as e:
            return f"Failed to open browser: {e}"
        
        return ""

    def _handle_voice_commands(self, lower: str, prompt: str) -> str:
        """Handle voice-specific commands"""
        if lower.strip() in ["stop", "stop reading", "stop talking", "shut up", "be quiet"]:
            try:
                self.stop_speaking()
            except Exception:
                pass
            return ""
        return ""

    def _handle_system_commands(self, lower: str, prompt: str) -> str:
        """Handle system commands"""
        if any(w in lower for w in ["open", "close", "volume", "mute"]):
            try:
                self.execute_command(prompt)
                return f"Executed system command: {prompt}"
            except Exception as e:
                return f"System command error: {e}"
        return ""

    def _handle_math_commands(self, lower: str, prompt: str) -> str:
        """Handle math commands"""
        if ("solve" in lower) or ("calculate" in lower) or any(ch.isdigit() for ch in lower):
            try:
                self.solve_math(prompt)
                return ""
            except Exception as e:
                return f"Math error: {e}"
        return ""

    def _handle_code_commands(self, lower: str, prompt: str) -> str:
        """Handle code generation commands"""
        if ("code" in lower) or ("program" in lower):
            try:
                self.generate_code(prompt)
                return ""
            except Exception as e:
                return f"Code generation error: {e}"
        return ""

    def _handle_database_commands(self, lower: str, prompt: str) -> str:
        """Handle database commands"""
        if ("run query" in lower) or ("mysql" in lower):
            try:
                result = self.handle_mysql_query(prompt)
                return "Query executed."
            except Exception as e:
                return f"Database error: {e}"
        
        if ("database" in lower) or ("sql" in lower):
            try:
                self.nl_to_sql(prompt)
                return "Attempted NL→SQL and executed."
            except Exception as e:
                return f"SQL translation error: {e}"
        return ""

    def _handle_email_commands(self, lower: str, prompt: str) -> str:
        """Handle email commands"""
        if ("email" in lower) or ("inbox" in lower):
            try:
                return self.handle_email_command(prompt) or ""
            except Exception as e:
                return f"Email error: {e}"
        return ""

    def _handle_news_commands(self, lower: str, prompt: str) -> str:
        """Handle news commands"""
        if "news" in lower:
            try:
                scope = "national" if any(k in lower for k in ["national", "india", "local"]) else "international"
                return self.get_news_summary(scope) or ""
            except Exception as e:
                return f"News error: {e}"
        return ""

    def _clean_output(self, text: str) -> str:
        """Clean output text by removing asterisks and formatting for better speech."""
        if not text:
            return text
        
        # Remove asterisks and other markdown formatting
        import re
        text = re.sub(r'\*+', '', text)  # Remove asterisks
        text = re.sub(r'#+', '', text)   # Remove hash marks
        text = re.sub(r'`+', '', text)   # Remove backticks
        text = re.sub(r'_+', '', text)   # Remove underscores
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Remove markdown links, keep text
        text = re.sub(r'\n+', ' ', text)  # Replace multiple newlines with space
        text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
        text = text.strip()
        
        return text

    def _handle_general_query(self, prompt: str) -> str:
        """Handle general AI queries"""
        try:
            # Check for specific name-related queries only
            lower = prompt.lower().strip()
            
            # Exact name queries
            if lower in ["what is your name", "what's your name", "who are you", "tell me your name", "what is your name?", "what's your name?", "who are you?", "tell me your name?"]:
                return "I am ALIAS, your AI assistant. I'm here to help you with various tasks and remember our conversations."
            
            # User name introduction queries
            elif lower.startswith("my name is ") or lower.startswith("i am ") or lower.startswith("call me "):
                # Extract user's name and store it
                if lower.startswith("my name is "):
                    user_name = prompt[11:].strip()
                elif lower.startswith("i am "):
                    user_name = prompt[5:].strip()
                elif lower.startswith("call me "):
                    user_name = prompt[8:].strip()
                else:
                    user_name = "User"
                
                # Store user's name in preferences
                try:
                    import sqlite3
                    conn = sqlite3.connect("alias_chat_history.db")
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    ''', ("user_name", user_name))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
                
                return f"Nice to meet you, {user_name}! I'm ALIAS, and I'll remember your name for our future conversations."
            
            # All other queries go to Gemini
            raw_response = self.gemini_chat(prompt)
            return self._clean_output(raw_response)
        except Exception as e:
            return f"AI query error: {e}"

    def analyze_text_async(
        self,
        prompt: str,
        on_result: Callable[[str], None],
        on_error: Optional[Callable[[str], None]] = None,
        on_activity: Optional[Callable[[bool], None]] = None,
    ) -> None:
        """Process text command asynchronously"""
        def worker():
            try:
                if on_activity:
                    on_activity(True)
                
                lower = prompt.lower()
                result = ""
                
                # Get recent chat history for context
                recent_history = self.get_recent_chat_history(5)
                context = ""
                if recent_history:
                    context = "Recent conversation context:\n"
                    for user_msg, assistant_msg, cmd_type, timestamp in reversed(recent_history[-3:]):
                        context += f"User: {user_msg}\nAssistant: {assistant_msg}\n"
                    context += "\nCurrent query: "
                
                # Get user's name from preferences for personalized responses
                user_name = "User"
                try:
                    import sqlite3
                    conn = sqlite3.connect("alias_chat_history.db")
                    cursor = conn.cursor()
                    cursor.execute('SELECT value FROM user_preferences WHERE key = ?', ("user_name",))
                    result = cursor.fetchone()
                    if result:
                        user_name = result[0]
                    conn.close()
                except Exception:
                    pass
                
                # Try each command handler in order
                result = (self._handle_voice_commands(lower, prompt) or
                         self._handle_web_commands(lower) or
                         self._handle_system_commands(lower, prompt) or
                         self._handle_math_commands(lower, prompt) or
                         self._handle_code_commands(lower, prompt) or
                         self._handle_database_commands(lower, prompt) or
                         self._handle_email_commands(lower, prompt) or
                         self._handle_news_commands(lower, prompt) or
                         self._handle_general_query(context + prompt if context else prompt))
                
                # Clean the result for better display and speech
                if result:
                    result = self._clean_output(result)
                
                # Determine command type for database storage
                command_type = "general"
                if lower.strip() in ["stop", "stop reading", "stop talking", "shut up", "be quiet"]:
                    command_type = "voice_control"
                elif any(w in lower for w in ["open", "close", "volume", "mute"]):
                    command_type = "system"
                elif ("solve" in lower) or ("calculate" in lower):
                    command_type = "math"
                elif ("code" in lower) or ("program" in lower):
                    command_type = "code"
                elif ("mysql" in lower) or ("database" in lower) or ("sql" in lower):
                    command_type = "database"
                elif ("email" in lower) or ("inbox" in lower):
                    command_type = "email"
                elif "news" in lower:
                    command_type = "news"
                elif lower.startswith("open youtube") or lower.startswith("open chrome"):
                    command_type = "web"
                
                on_result(result or "")
                
                # Save to database
                if result:
                    try:
                        self.save_chat_message(prompt, result, command_type)
                        self.update_query_memory(prompt, result, True)
                    except Exception:
                        pass
                
                # Speak result if TTS enabled
                if result and TTS_ENABLED:
                    try:
                        self.speak(result)
                    except Exception:
                        pass
                        
            except Exception as e:
                if on_error:
                    on_error(str(e))
            finally:
                if on_activity:
                    on_activity(False)

        threading.Thread(target=worker, daemon=True).start()

    def analyze_file_async(
        self,
        file_path: str,
        on_progress: Optional[Callable[[int], None]] = None,
        on_result: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_activity: Optional[Callable[[bool], None]] = None,
    ) -> None:
        """Analyze file asynchronously"""
        def worker():
            try:
                if on_activity:
                    on_activity(True)
                
                if on_progress:
                    on_progress(10)
                
                summary = self.analyze_document(file_path)
                
                if on_progress:
                    on_progress(90)
                
                if on_result:
                    on_result(summary or "")
                
                # Speak result if TTS enabled
                if summary and TTS_ENABLED:
                    try:
                        self.speak(summary)
                    except Exception:
                        pass
                        
            except Exception as e:
                if on_error:
                    on_error(str(e))
            finally:
                if on_progress:
                    on_progress(100)
                if on_activity:
                    on_activity(False)

        threading.Thread(target=worker, daemon=True).start()