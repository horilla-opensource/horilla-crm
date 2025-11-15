# Horilla CRM

<div align="center">
  <img src="static/favicon.ico" alt="Horilla CRM Logo" width="64" height="64">
  <h3>Enterprise Customer Relationship Management System</h3>
  <p>A comprehensive CRM solution designed for enterprise-level customer engagement, sales tracking, and business process automation.</p>
</div>

[![License](https://img.shields.io/badge/license-LGPL-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/django-5.2+-green.svg)](https://djangoproject.com)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://docker.com)

## ✨ Features

### 🏢 **Core CRM Modules**
- **👥 People Management**
  - **Accounts**: Manage companies and organizations with detailed profiles
  - **Contacts**: Individual contact management with relationship tracking
  - **Roles & Permissions**: Granular access control and user management

- **💼 Sales Pipeline**
  - **Leads**: Lead capture, qualification, and nurturing
  - **Opportunities**: Deal tracking with customizable sales stages
  - **Forecasting**: Revenue predictions and sales analytics
  - **Big Deal Alerts**: Automated notifications for high-value opportunities

- **📊 Marketing & Campaigns**
  - **Campaign Management**: Multi-channel campaign creation and tracking
  - **Campaign Analytics**: Performance metrics and ROI analysis
  - **Lead Source Tracking**: Attribution and conversion analysis

- **📅 Activity & Communication**
  - **Activity Tracking**: Meetings, calls, emails, and task management
  - **Calendar Integration**: Unified scheduling and event management
  - **Timeline View**: Chronological activity history
  - **Email Integration**: Built-in email composer with templates

- **📈 Analytics & Reporting**
  - **Interactive Dashboards**: Customizable widgets and charts
  - **Advanced Reports**: Detailed analytics across all modules
  - **Data Export**: CSV, Excel export capabilities
  - **Real-time Notifications**: WebSocket-based live updates

### 🌐 **Technical Features**
- **Multi-language Support**: 25+ languages including English, Arabic, German, French, Korean
- **Multi-currency**: Global currency support with conversion
- **Real-time Updates**: WebSocket integration for live notifications
- **Advanced Search**: Global search across all modules
- **Import/Export**: Bulk data operations with CSV/Excel support
- **Audit Trail**: Complete activity logging and history tracking
- **Responsive Design**: Mobile-friendly interface
- **Dark/Light Themes**: Customizable UI preferences

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local development)
- PostgreSQL (recommended for production)

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/horilla-opensource/horilla-crm.git
   cd horilla-crm
   ```

2. **Configure environment** (optional)
   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

3. **Start development environment**
   ```bash
   make dev
   # or
   docker-compose up --build
   ```

4. **Start production environment**
   ```bash
   make prod
   # or
   docker-compose --profile production up --build -d
   ```

5. **Create superuser**
   ```bash
   make shell
   python manage.py createsuperuser
   ```

6. **Access the application**
   - Development: http://localhost:8000
   - Production: http://localhost (with nginx)

### Option 2: Local Development

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure database**
   ```bash
   python manage.py migrate
   ```

3. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

4. **Run development server**
   ```bash
   python manage.py runserver
   ```

## 🐳 Docker Configuration

### Available Commands
```bash
make help     # Show all commands
make dev      # Development server
make prod     # Production with nginx
make build    # Build images
make stop     # Stop services
make logs     # View logs
make shell    # Open container shell
make db-shell # Open PostgreSQL shell
make clean    # Clean up
```

### Services
- **Web**: Django app with Uvicorn ASGI server (port 8000)
- **Database**: PostgreSQL 16 (port 5432)
- **Nginx**: Reverse proxy for production (port 80)

### Environment Variables
```bash
# PostgreSQL Database
POSTGRES_DB=horilla_db
POSTGRES_USER=horilla_user
POSTGRES_PASSWORD=horilla_pass

# Django Configuration
DEBUG=1
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000

# Database URL
DATABASE_URL=postgres://horilla_user:horilla_pass@db:5432/horilla_db
```

## 🏗️ Architecture

### Technology Stack
- **Backend**: Django 5.2+ with Python 3.12+
- **Database**: PostgreSQL (recommended), SQLite (development)
- **Web Server**: Uvicorn ASGI server with WebSocket support
- **Frontend**: HTML5, TailwindCSS, HTMX for dynamic interactions
- **Real-time**: Django Channels for WebSocket communication
- **Task Queue**: APScheduler for background tasks
- **File Storage**: WhiteNoise for static files

## 🔧 Configuration

### Database Configuration

**SQLite (Development)**
```python
DATABASE_URL=sqlite:///db.sqlite3
```

**PostgreSQL (Production)**
```python
DATABASE_URL=postgres://username:password@localhost:5432/horilla_crm
```


### Email Configuration
```python
# SMTP Settings
EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST='smtp.gmail.com'
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER='your-email@gmail.com'
EMAIL_HOST_PASSWORD='your-app-password'
```

### Redis Configuration (Optional)
```python
# For production WebSocket scaling
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
```

## 🔐 Security Features

- **Role-based Access Control**: Granular permissions system
- **CSRF Protection**: Built-in Django CSRF protection
- **SQL Injection Protection**: Django ORM with parameterized queries
- **XSS Protection**: Template auto-escaping and CSP headers
- **Secure Headers**: Security middleware with HSTS, X-Frame-Options
- **Password Validation**: Strong password requirements
- **Session Security**: Secure session configuration
- **API Rate Limiting**: Built-in rate limiting for API endpoints

## 📊 API & Integrations

### REST API
- RESTful API endpoints for all modules
- Token-based authentication
- Pagination and filtering support
- Swagger/OpenAPI documentation

### Webhook Support
- Outbound webhooks for key events
- Configurable event triggers
- Retry mechanism with exponential backoff

### Import/Export
- CSV import/export for all data
- Excel file support
- Bulk operations API
- Data validation and error reporting

## 🌍 Internationalization

### Supported Languages
- English (en)
- Arabic (ar)
- German (de)
- French (fr)
- More languages coming soon


### Adding New Languages
1. Create translation files: `python manage.py makemessages -l <language_code>`
2. Translate strings in `.po` files
3. Compile messages: `python manage.py compilemessages`
4. Add language to `ALLOWED_LANGUAGES` in settings

## 📈 Performance Optimization

### Database Optimization
- Database indexing on frequently queried fields
- Query optimization with select_related and prefetch_related
- Connection pooling configuration
- Read replica support

### Caching Strategy
- Template fragment caching
- Database query caching
- Static file caching with long expiry
- Redis caching layer (optional)

### Frontend Optimization
- Minified CSS and JavaScript
- Image optimization and lazy loading
- HTMX for dynamic content without full page reloads
- CDN support for static assets


## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure strong `SECRET_KEY`
- [ ] Set up production database (PostgreSQL)
- [ ] Configure email settings
- [ ] Set up SSL/HTTPS
- [ ] Configure static file serving
- [ ] Set up backup strategy
- [ ] Configure monitoring and logging
- [ ] Set up Redis for caching (optional)
- [ ] Configure firewall and security groups

### Deployment Options

1. **Docker Compose** (Recommended)
   ```bash
   docker-compose --profile production up -d
   ```

2. **Kubernetes**
   - Helm charts available in `/k8s` directory
   - Supports horizontal scaling
   - Includes health checks and rolling updates

3. **Traditional Server**
   - Systemd service files included
   - Nginx configuration templates
   - Debian/Ubuntu package installation

4. **Cloud Platforms**
   - AWS ECS/Fargate ready
   - Google Cloud Run compatible
   - Azure Container Instances support

## 🔍 Monitoring & Logging

### Application Logs
```bash
# View application logs
docker-compose logs -f web

# View database logs
docker-compose logs -f db

# View nginx logs
docker-compose logs -f nginx
```

### Health Checks
- **Application**: `GET /health`
- **Database**: Built-in connection monitoring
- **WebSocket**: Real-time connection status

### Metrics Collection
- User activity tracking
- Performance metrics
- Error rate monitoring
- Resource usage statistics

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `python manage.py test`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Create a Pull Request

### Code Style
- Follow PEP 8 for Python code
- Use Black for code formatting
- Run pylint for code analysis
- Write docstrings for all functions and classes

### Reporting Issues
- Use GitHub Issues for bug reports
- Include detailed reproduction steps
- Provide environment information
- Add relevant logs and screenshots

## 📚 Documentation

### User Documentation
- **Admin Guide**: Complete administration documentation
- **User Manual**: End-user feature documentation
- **API Reference**: Complete API documentation
- **Integration Guide**: Third-party integration examples

### Developer Documentation
- **Architecture Guide**: System design and components
- **Contributing Guide**: Development setup and guidelines
- **API Documentation**: REST API reference
- **Deployment Guide**: Production deployment instructions

## 🆘 Support

### Community Support
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community Q&A and discussions
- **Documentation**: Comprehensive guides and tutorials

### Enterprise Support
- Professional support available
- Custom development services
- Training and onboarding

## 📋 System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 20GB
- **OS**: Linux, Windows, macOS
- **Python**: 3.12+
- **Database**: PostgreSQL 12+, MySQL 8.0+, or SQLite 3.x

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ SSD
- **Database**: PostgreSQL 16+
- **Redis**: 6.0+ (for caching)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Django community for the excellent framework
- All contributors who have helped improve this project
- Open source libraries that make this project possible

---

<div align="center">
  <p>Made with ❤️ by the Horilla team</p>
  <p>
    <a href="https://github.com/horilla-opensource/horilla-crm">GitHub</a> •
    <a href="#documentation">Documentation</a> •
    <a href="#support">Support</a>
  </p>
</div>
