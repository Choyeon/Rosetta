# 🌸 Rosetta - Modern Blog System

<div align="center">

![Rosetta](https://img.shields.io/badge/Rosetta-Blog%20System-3C5A78?style=for-the-badge)
![Nuxt 4](https://img.shields.io/badge/Nuxt-4.0-00DC82?style=for-the-badge&logo=nuxt.js)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=for-the-badge&logo=fastapi)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=for-the-badge&logo=typescript)
![Status](https://img.shields.io/badge/Status-80%25%20Complete-success?style=for-the-badge)

**A beautiful, modern, and full-featured blog system with a elegant blue-themed frontend and powerful admin panel.**

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [Screenshots](#screenshots)

</div>

---

## ✨ Features

### 🎨 Frontend (Nuxt 4)
- ✅ **Modern UI** - Beautiful blue-themed design with Playfair Display typography
- ✅ **Responsive** - Perfect on mobile, tablet, and desktop
- ✅ **Multi-language** - 4 languages (中文/English/日本語/繁體中文)
- ✅ **Authentication** - JWT-based secure login system
- ✅ **OOBE Wizard** - First-time installation guide
- ✅ **Comments** - Nested comments with replies
- ✅ **SEO Ready** - Meta tags and structured data
- ✅ **Dark Mode Ready** - Infrastructure in place

### 🚀 Backend (FastAPI)
- ✅ **Async/Await** - High-performance async operations
- ✅ **Type-Safe** - Pydantic validation throughout
- ✅ **Multi-language** - Content localization support
- ✅ **JWT Auth** - Secure token-based authentication
- ✅ **SQLAlchemy 2.0** - Modern ORM with async support
- ✅ **Redis Cache** - Optional caching layer
- ✅ **Alembic** - Database migrations
- ✅ **RESTful API** - Well-structured endpoints

### 📱 Pages Available

#### Public Pages
- 🏠 **Homepage** - Hero banner, featured posts, categories
- 📝 **Posts** - List with pagination, search, filters
- 📄 **Post Detail** - Full content, comments, likes, related posts
- 🏷️ **Categories** - Grid layout with post counts
- 📅 **Archive** - Yearly/monthly post archives
- 🔐 **Login/Register** - User authentication
- ⚙️ **OOBE** - Installation wizard

#### Admin Panel
- 📊 **Dashboard** - Statistics and overview
- 📝 Posts Management (TODO)
- 🏷️ Categories Management (TODO)
- 🏷️ Tags Management (TODO)
- 💬 Comments Moderation (TODO)
- 👥 Users Management (TODO)
- ⚙️ Settings (TODO)

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.11+ (for backend)
- **pnpm** (recommended) or npm
- **PostgreSQL** or **SQLite** (for database)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/rosetta.git
cd rosetta
```

### 2. Start Backend

```bash
# Install backend dependencies
cd backend
uv sync

# Start backend server
uv run uvicorn backend.main:app --reload --port 8000
```

Backend will be available at: http://localhost:8000

### 3. Start Frontend

**Windows:**
```bash
cd frontend
setup.bat
```

**Linux/Mac:**
```bash
cd frontend
chmod +x setup.sh
./setup.sh
```

**Manual:**
```bash
cd frontend
pnpm install
pnpm dev
```

Frontend will be available at: http://localhost:3000

### 4. Complete OOBE Setup

1. Visit http://localhost:3000/oobe
2. Configure database settings
3. Enter site information
4. Create admin account
5. Wait for installation to complete
6. Start using your blog! 🎉

---

## 📚 Documentation

### Frontend Documentation
- 📖 [INDEX.md](./frontend/INDEX.md) - Documentation navigation
- 🚀 [README.md](./frontend/README.md) - Setup and installation
- 🔧 [IMPLEMENTATION.md](./frontend/IMPLEMENTATION.md) - Developer guide
- 📊 [PROJECT_STATUS.md](./frontend/PROJECT_STATUS.md) - Progress tracking
- 📋 [CHECKLIST.md](./frontend/CHECKLIST.md) - Complete checklist
- 📝 [完成总结.md](./frontend/完成总结.md) - Chinese summary
- 📊 [SUMMARY.md](./frontend/SUMMARY.md) - Visual summary

### Backend Documentation
- 📖 [CLAUDE.md](./backend/CLAUDE.md) - Backend overview
- 🏗️ [AGENTS.md](./backend/AGENTS.md) - Repository guidelines
- 📚 [docs/api_reference.md](./backend/docs/api_reference.md) - API reference
- 🐛 [docs/error_codes.md](./backend/docs/error_codes.md) - Error codes

---

## 🏗️ Architecture

### Frontend Stack
```
Nuxt 4 (Vue 3 + TypeScript)
├── NuxtUI - Component library (Admin)
├── TailwindCSS - Styling
├── Pinia - State management
├── @nuxtjs/i18n - Internationalization
└── marked - Markdown rendering
```

### Backend Stack
```
FastAPI (Python 3.11+)
├── SQLAlchemy 2.0 - ORM (Async)
├── Pydantic v2 - Validation
├── Alembic - Migrations
├── Redis - Caching (optional)
├── JWT - Authentication
└── Uvicorn - ASGI server
```

### Project Structure

```
rosetta/
├── frontend/                 # Nuxt 4 frontend
│   ├── app/
│   │   ├── pages/           # Route pages
│   │   ├── layouts/         # Layouts
│   │   └── middleware/      # Route guards
│   ├── components/          # Vue components
│   ├── composables/         # API composables
│   ├── stores/              # Pinia stores
│   ├── types/               # TypeScript types
│   └── locales/             # i18n translations
│
└── backend/                 # FastAPI backend
    ├── api/                 # API routes
    ├── models/              # SQLAlchemy models
    ├── schemas/             # Pydantic schemas
    ├── services/            # Business logic
    ├── repositories/        # Data access
    ├── core/                # Core utilities
    └── migrations/          # Alembic migrations
```

---

## 🎨 Design System

### Color Palette (Blue Theme)

```css
/* Primary Colors */
--primary: #3C5A78;        /* Muted slate blue */
--primary-hover: #2E4760;  /* Darker slate */

/* Neutrals */
--background: #F7F5F1;     /* Soft off-white */
--surface: #FFFFFF;        /* White */
--border: #E7E3DA;         /* Light border */
--text: #1E2227;           /* Dark text */
--text-muted: #6B7077;     /* Secondary text */
```

### Typography

- **Display Font**: Playfair Display (Serif, 500-700)
- **Body Font**: Inter (Sans-serif, 400-500)
- **Base Size**: 16px (1rem)
- **Scale**: 1.25 (Major Third)

### Spacing

```
4px • 8px • 12px • 16px • 24px • 32px • 48px • 64px
```

---

## 🌐 API Endpoints

### Authentication
```
POST   /api/users/register     - Register new user
POST   /api/users/login        - Login with credentials
POST   /api/users/refresh      - Refresh access token
POST   /api/users/logout       - Logout
```

### Posts
```
GET    /api/posts              - Get posts list
GET    /api/posts/{slug}       - Get post detail
POST   /api/posts              - Create post (Admin)
PUT    /api/posts/{id}         - Update post (Admin)
DELETE /api/posts/{id}         - Delete post (Admin)
POST   /api/posts/{id}/like    - Like/unlike post
```

### Categories & Tags
```
GET    /api/categories         - Get categories
GET    /api/tags               - Get tags
POST   /api/categories         - Create category (Admin)
POST   /api/tags               - Create tag (Admin)
```

### Comments
```
GET    /api/posts/{id}/comments       - Get comments
POST   /api/posts/{id}/comments       - Create comment
DELETE /api/comments/{id}             - Delete comment (Admin)
```

### Core
```
GET    /api/config             - Get site configuration
GET    /api/navigations        - Get navigation items
GET    /api/friend-links       - Get friend links
GET    /api/archive            - Get archive
```

**Full API Documentation**: http://localhost:8000/docs

---

## 📊 Progress Status

### Overall: 80% Complete ✅

| Module | Status | Completion |
|--------|--------|------------|
| 🏗️ Infrastructure | ✅ Complete | 100% |
| 🔐 Authentication | ✅ Complete | 100% |
| 🌐 i18n Support | ✅ Complete | 100% |
| 🎨 Design System | ✅ Complete | 100% |
| 📱 Public Pages | 🟡 Partial | 75% |
| ⚙️ Admin Panel | 🟡 Partial | 40% |
| 📚 Documentation | ✅ Complete | 100% |

### What's Working
- ✅ Homepage with hero and featured posts
- ✅ Posts list with pagination and filters
- ✅ Post detail with comments and likes
- ✅ Categories and archive pages
- ✅ Login and registration
- ✅ OOBE installation wizard
- ✅ Admin dashboard with stats
- ✅ Multi-language support
- ✅ Responsive design

### What's Next
- 🚧 Category/tag detail pages
- 🚧 Admin posts CRUD
- 🚧 Markdown editor integration
- 🚧 User profile pages
- 🚧 Admin settings page
- 🚧 Additional static pages

---

## 🛠️ Development

### Frontend Development

```bash
cd frontend

# Install dependencies
pnpm install

# Start dev server
pnpm dev

# Build for production
pnpm build

# Preview production build
pnpm preview

# Type check
pnpm typecheck
```

### Backend Development

```bash
cd backend

# Install dependencies
uv sync

# Start dev server
uv run uvicorn backend.main:app --reload

# Run migrations
uv run python -m backend.migrations upgrade

# Create migration
uv run python -m backend.migrations revision -m "description" --autogenerate

# Run tests
uv run pytest
```

---

## 📝 Environment Variables

### Frontend `.env`
```env
API_BASE_URL=http://localhost:8000/api
NUXT_PUBLIC_API_BASE=http://localhost:8000/api
```

### Backend `.env`
```env
# Application
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite+aiosqlite:///./rosetta.db
# or
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/rosetta

# Redis (optional)
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Site
SITE_NAME=Rosetta
SITE_URL=http://localhost:3000
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Nuxt** - The Intuitive Vue Framework
- **FastAPI** - Modern Python web framework
- **TailwindCSS** - Utility-first CSS framework
- **NuxtUI** - Fully styled and customizable components
- **Pinia** - The Vue Store
- **SQLAlchemy** - The Python SQL Toolkit

---

## 📞 Support

- 📖 **Documentation**: Check the [INDEX.md](./frontend/INDEX.md)
- 🐛 **Bug Reports**: Open an issue on GitHub
- 💬 **Discussions**: Join our community
- 📧 **Email**: support@rosetta.example

---

## 🎯 Roadmap

### Version 1.0 (Current - 80% Complete)
- [x] Core infrastructure
- [x] Authentication system
- [x] Public pages
- [x] OOBE wizard
- [ ] Admin CRUD pages
- [ ] Markdown editor

### Version 1.1 (Planned)
- [ ] Search functionality
- [ ] RSS feed
- [ ] Social sharing
- [ ] SEO optimization
- [ ] Performance optimization

### Version 2.0 (Future)
- [ ] Dark mode
- [ ] Email notifications
- [ ] Advanced analytics
- [ ] Plugin system
- [ ] Theme customization

---

<div align="center">

**Built with ❤️ using Nuxt 4, FastAPI, and modern web technologies**

⭐ Star us on GitHub if you find this project useful!

</div>
