# A.L.I.A.S. - Advanced Logical Interface and Assistant System

A sophisticated AI-powered desktop assistant built with PyQt6, featuring voice recognition, document analysis, system control, and intelligent conversation capabilities. ALIAS combines cutting-edge AI technology with an elegant, minimal black-and-white interface for seamless human-computer interaction.

## 🚀 Features

### Core Capabilities
- 🎤 **Always-On Voice Recognition**: Continuous speech recognition without button presses
- 🧠 **AI-Powered Intelligence**: Powered by Google Gemini for natural language understanding
- 📄 **Document Analysis**: Upload and analyze TXT, PDF, and DOCX files with AI summarization
- 🎯 **System Control**: Voice commands for opening applications, volume control, and system management
- 🧮 **Math & Code Generation**: Solve mathematical problems and generate Python code
- 📧 **Email Integration**: Read and send emails through voice commands
- 📰 **News Updates**: Get summarized news from various sources
- 🗄️ **Database Management**: Create and manage MySQL databases with natural language

### Advanced Features
- 🔐 **Identity Verification**: Camera-based security check with configurable modes
- 💬 **Persistent Memory**: Remembers conversations and learns from interactions
- 🎨 **Modern UI**: Sleek PyQt6 interface with animated elements and smooth interactions
- 🔊 **Text-to-Speech**: Natural voice responses with customizable settings
- 📊 **Progress Tracking**: Real-time progress indicators for file analysis
- 🎭 **Animated Interface**: Pulsing orb indicator and smooth animations

## 📋 Requirements

- **Operating System**: Windows 10/11 (64-bit recommended)
- **Python**: 3.10+ (recommended)
- **Hardware**: Microphone for voice features, webcam for identity verification
- **Internet**: Required for AI services and voice recognition

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd frday3.0
```

### 2. Install Dependencies
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Note**: If PyAudio installation fails on Windows, install a matching wheel for your Python version:
```bash
pip install PyAudio-0.2.11-cp310-cp310-win_amd64.whl
```

### 3. Environment Configuration
Create a `.env` file in the project directory:

```ini
# Required: Get your API key from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: News and email configuration
NEWS_COUNTRY=us
EMAIL_ADDRESS=your_email@example.com
EMAIL_PASSWORD=your_app_password

# Security: Identity verification mode
ALIAS_IDENTITY_MODE=lenient  # Options: off | lenient | strict
```

## 🚀 Quick Start

### Launch ALIAS
```bash
python run_friday_qt.py
```

**Alternative launch method:**
```bash
python friday.py
```

### First Run
1. **Identity Check**: ALIAS will perform a camera-based identity verification
2. **Voice Setup**: Ensure your microphone is working and accessible
3. **Start Chatting**: Type or speak your commands to interact with ALIAS

## 💬 Voice Commands

### System Control
- `"open chrome"` - Launch Google Chrome
- `"open youtube [search term]"` - Search YouTube
- `"open chrome and search [query]"` - Google search
- `"close [application]"` - Close specified application
- `"volume up/down"` - Adjust system volume
- `"mute"` - Mute/unmute system audio

### AI Interactions
- `"solve [math problem]"` - Solve mathematical expressions
- `"calculate [expression]"` - Perform calculations
- `"generate code for [description]"` - Generate Python code
- `"what is [topic]"` - Ask general questions
- `"stop"` - Stop current speech output

### File Operations
- Upload files through the UI for AI analysis
- Supports TXT, PDF, and DOCX formats
- Automatic summarization and key point extraction

### Email Commands
- `"read emails"` - Read latest emails
- `"send email to [address] subject: [subject] body: [message]"` - Send email

### News & Information
- `"get news"` - International news summary
- `"get national news"` - Local news summary

## 🔧 Configuration

### Identity Verification Modes
- **`off`**: Skip identity check entirely
- **`lenient`** (default): Pass on face detection or timeout
- **`strict`**: Require eye detection for access

### TTS Settings
- Toggle speech output on/off via the UI
- Adjust speech rate and voice in the system

### Database Configuration
- MySQL integration for advanced database operations
- Natural language to SQL translation
- Automatic database and table creation

## 📁 Project Structure

```
frday3.0/
├── run_friday_qt.py      # Main PyQt6 application launcher
├── friday.py             # Core AI logic and functions
├── qt_friday_ui.py       # PyQt6 user interface
├── qt_backend.py         # Backend processing and command handling
├── requirements.txt      # Python dependencies
├── alias_chat_history.db # SQLite database for conversation history
├── build_windows_exe.bat # Windows executable build script
└── README.md            # This documentation
```

## 🔨 Building Executable

### Create Windows Executable
1. Install PyInstaller:
   ```bash
   python -m pip install pyinstaller
   ```

2. Build the executable:
   ```bash
   pyinstaller --noconfirm --onefile --name ALIASAI --windowed run_friday_qt.py
   ```

3. Find your executable in `dist/ALIASAI.exe`

## 🐛 Troubleshooting

### Common Issues

**PyQt6 Import Errors**
- Ensure you're using Python 3.10+
- Reinstall requirements: `pip install -r requirements.txt`

**Microphone Not Working**
- Check Windows Privacy Settings > Microphone
- Ensure microphone is set as default recording device
- Test microphone in other applications

**TTS Not Speaking**
- Verify audio output device is active
- Check TTS toggle in the UI
- Try different voice settings in Windows

**Identity Check Failing**
- Ensure webcam is accessible
- Check camera permissions in Windows
- Try different identity modes in `.env`

**API Errors**
- Verify your Gemini API key is correct
- Check internet connection
- Ensure API key has proper permissions

## 🌟 Advanced Usage

### Custom Commands
Extend ALIAS capabilities by modifying `qt_backend.py`:

```python
def _handle_custom_commands(self, lower: str, prompt: str) -> str:
    if "custom" in lower:
        # Your custom logic here
        return "Custom response"
```

### Database Integration
- Create databases with natural language: `"create a database for students"`
- Run SQL queries: `"run query SELECT * FROM users"`
- Natural language to SQL: `"show me all users from last month"`

### Memory and Learning
- ALIAS remembers your name and preferences
- Learns from conversation patterns
- Stores chat history for context

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

We welcome contributions! Please feel free to submit issues, feature requests, or pull requests to improve ALIAS.

---

**Experience the future of human-computer interaction with A.L.I.A.S. 🚀**
