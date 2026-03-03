# AI Interviewer System

An intelligent AI-powered interview system built with Django and Google Gemini AI.

## Features

- 🎤 AI-powered interview questions based on job role
- 📝 Automatic answer evaluation
- 🔒 Anti-cheating mechanisms (tab switching, copy/paste detection)
- 📧 Email notifications with results
- 👥 User registration and admin management
- ⏱️ 20-minute interview timer
- 🎯 5 questions per interview session

## Tech Stack

- Django 5.2
- Google Generative AI (Gemini)
- SQLite Database
- Tailwind CSS

## Setup Instructions

1. Clone the repository
```bash
git clone https://github.com/Naveen5577/AI_Interviewer.git
cd AI_Interviewer
```

2. Install dependencies
```bash
pip install -r req.txt
```

3. Set up environment variables
Create a `.env` file with:
```
GOOGLE_API_KEY=your_google_api_key_here
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

4. Run migrations
```bash
python manage.py migrate
```

5. Create superuser
```bash
python manage.py createsuperuser
```

6. Run the server
```bash
python manage.py runserver
```

## Usage

- **User Registration**: `/register/`
- **User Login**: `/user-login/`
- **Admin Login**: `/admin-login/` (username: admin, password: admin)
- **Start Interview**: `/start/`

## Security Note

⚠️ Never commit your `.env` file or expose API keys in production!

## License

MIT License
