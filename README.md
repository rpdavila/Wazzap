# Wazzap

A real-time chat application with support for direct messages and group chats.

## Features

- **Real-time messaging** via WebSocket
- **Direct messages** and **group chats**
- **Media sharing** (images and GIFs)
- **Read receipts** and message status tracking
- **User-friendly interface** - most actions can be done directly in the UI

## Quick Start

Run the application with a single command:

```bash
python start.py
```

This will start both the backend API server (port 8000) and frontend development server (port 5173).

The application will be available at `http://localhost:5173`

## First Steps

1. **Register** a new account with a username and PIN (4-8 digits)
2. **Login** with your credentials
3. **Browse users** to start new conversations
4. **Create group chats** or send direct messages
5. **Share media** by uploading images or GIFs

## API Documentation

Once the backend is running, you can access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Svelte 4
- **Database**: SQLite
- **Real-time**: WebSocket

## Project Structure

```
Wazzap/
├── backend/          # FastAPI backend server
├── frontend/         # Svelte frontend application
└── start.py          # Main entry point (starts both servers)
```

For detailed setup instructions, see the README files in the `backend/` and `frontend/` directories.
