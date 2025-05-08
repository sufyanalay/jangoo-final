# Django REST Framework Backend for Gadget Repair & Academic Support Platform

A comprehensive backend system built with Django REST Framework that supports gadget repair services, academic tutoring, and real-time chat functionality.

## Features

- User authentication with JWT and role-based access control (students, teachers, technicians)
- Gadget repair request submission and management
- Academic question submission and tutoring support
- Real-time chat using Django Channels and WebSockets
- Rating and feedback system for service providers
- Earnings dashboard for experts/tutors
- Educational resources hub

## Tech Stack

- Django 4.2.10
- Django REST Framework 3.14.0
- MongoDB (with mongoengine)
- Channels for WebSockets/real-time features
- JWT Authentication

## Setup Instructions

### Prerequisites

- Python 3.8+
- MongoDB
- Redis (for Channels)

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd <project-directory>
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration values
```

5. Run migrations (this will set up the necessary structure in MongoDB):

```bash
python manage.py migrate
```

6. Create a superuser:

```bash
python manage.py createsuperuser
```

7. Start the development server:

```bash
python manage.py runserver
```

The API will be accessible at http://localhost:8000/

## API Documentation

API documentation is available at:

- Swagger UI: `/swagger/`
- ReDoc: `/redoc/`

## Main API Endpoints

- Authentication: `/api/auth/`
- Repair Requests: `/api/repair/`
- Academic Questions: `/api/academic/`
- Resources: `/api/resources/`
- Reviews: `/api/reviews/`

## WebSocket Endpoints

- Chat: `ws://localhost:8000/ws/chat/<room_id>/`

## Security Features

- JWT Authentication
- Role-based access control
- Secure password handling
- Input validation and sanitization

## Deployment Considerations

- Use proper MongoDB security configuration
- Set up Redis with password protection
- Use a proper ASGI server (Daphne or Uvicorn)
- Configure CORS for your frontend domains
- Use HTTPS in production