# Rosetta Frontend - Setup & Installation Guide

## 📋 Prerequisites

- Node.js 18+ or later
- pnpm (recommended) or npm
- Backend API running on `http://localhost:8000`

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend
pnpm install
```

### 2. Configure Environment

Create a `.env` file in the `frontend/` directory:

```env
# API Configuration
API_BASE_URL=http://localhost:8000/api

# Nuxt Configuration
NUXT_PUBLIC_API_BASE=http://localhost:8000/api
```

### 3. Start Development Server

```bash
pnpm dev
```

The frontend will be available at `http://localhost:3000`

### 4. First-Time Setup (OOBE)

1. Navigate to `http://localhost:3000/oobe`
2. Follow the installation wizard:
   - Configure database connection
   - Set up site information
   - Create admin account
3. After completion, you'll be redirected to the homepage

## 📦 Build for Production

```bash
# Build the application
pnpm build

# Preview production build
pnpm preview

# Generate static site (SSG)
pnpm generate
```

## 🗂️ Project Structure

```
frontend/
├── app/
│   ├── pages/              # Route pages
│   │   ├── index.vue       # Homepage
│   │   ├── login.vue       # Login page
│   │   ├── register.vue    # Registration page
│   │   ├── oobe.vue        # Installation wizard
│   │   ├── archive.vue     # Archive page
│   │   ├── posts/
│   │   │   ├── index.vue   # Posts list
│   │   │   └── [slug].vue  # Post detail
│   │   ├── categories/
│   │   │   ├── index.vue   # Categories list
│   │   │   └── [slug].vue  # Category detail
│   │   ├── tags/
│   │   │   ├── index.vue   # Tags list
│   │   │   └── [slug].vue  # Tag detail
│   │   └── admin/          # Admin pages
│   │       ├── index.vue   # Dashboard
│   │       └── posts/      # Post management
│   └── assets/
│       └── css/
│           └── main.css    # Global styles
├── components/
│   ├── AppHeader.vue       # Site header
│   ├── AppFooter.vue       # Site footer
│   ├── PostCard.vue        # Post card component
│   ├── CommentItem.vue     # Comment component
│   ├── AdminSidebar.vue    # Admin sidebar
│   └── AdminHeader.vue     # Admin header
├── composables/
│   ├── useAPI.ts           # API wrapper
│   ├── usePosts.ts         # Posts API
│   ├── useAuth.ts          # Auth API
│   ├── useCore.ts          # Core API (categories, tags, etc.)
│   ├── useUsers.ts         # Users API
│   └── useOOBE.ts          # OOBE API
├── stores/
│   └── auth.ts             # Auth state management
├── types/
│   └── api.ts              # TypeScript type definitions
├── locales/
│   ├── zh.json             # Chinese (Simplified)
│   ├── en.json             # English
│   ├── ja.json             # Japanese
│   └── zh_Hant.json        # Chinese (Traditional)
├── layouts/
│   ├── default.vue         # Default layout
│   └── admin.vue           # Admin layout
├── middleware/
│   └── auth.ts             # Auth middleware
├── nuxt.config.ts          # Nuxt configuration
├── app.config.ts           # App configuration
├── tailwind.config.ts      # Tailwind configuration
└── package.json            # Dependencies

```

## 🔧 Configuration Files

### nuxt.config.ts

```typescript
export default defineNuxtConfig({
  modules: [
    '@nuxt/ui',
    '@nuxtjs/i18n',
    '@pinia/nuxt'
  ],
  
  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE_URL || 'http://localhost:8000/api'
    }
  },
  
  i18n: {
    locales: [
      { code: 'zh', name: '简体中文', file: 'zh.json' },
      { code: 'en', name: 'English', file: 'en.json' },
      { code: 'ja', name: '日本語', file: 'ja.json' },
      { code: 'zh_Hant', name: '繁體中文', file: 'zh_Hant.json' }
    ],
    defaultLocale: 'zh',
    lazy: true,
    langDir: 'locales'
  }
})
```

### app.config.ts

```typescript
export default defineAppConfig({
  ui: {
    primary: 'blue',
    gray: 'slate',
    icons: {
      dynamic: true
    }
  }
})
```

## 🎨 Design System

### Color Palette

```css
/* Primary Colors */
--color-background: #F7F5F1;  /* Soft off-white */
--color-surface: #FFFFFF;      /* White */
--color-border: #E7E3DA;       /* Hairline borders */
--color-text: #1E2227;         /* Primary text */
--color-text-muted: #6B7077;   /* Secondary text */
--color-accent: #3C5A78;       /* Muted slate blue */
--color-accent-hover: #2E4760; /* Darker slate */
```

### Typography

- **Display Font**: Playfair Display (serif, 500-700)
- **Body Font**: Inter (400-500)
- **Base Size**: 16px (1rem)
- **Line Height**: 1.5 (body), 1.2 (headings)

### Spacing Scale

- `space-1`: 0.25rem (4px)
- `space-2`: 0.5rem (8px)
- `space-3`: 0.75rem (12px)
- `space-4`: 1rem (16px)
- `space-6`: 1.5rem (24px)
- `space-8`: 2rem (32px)
- `space-12`: 3rem (48px)

## 🔐 Authentication Flow

1. User logs in via `/login`
2. Backend returns JWT access token + refresh token
3. Tokens stored in `localStorage`
4. `useAPI` composable automatically adds `Authorization` header
5. On 401 error, attempts to refresh token
6. If refresh fails, redirects to login

## 🌐 API Integration

All API calls use the `useAPI` composable:

```typescript
// Example: Fetch posts
const { data, error, pending } = await useAPI('/posts', {
  query: { page: 1, page_size: 12 }
})

// Example: Create post
const { data } = await useAPI('/posts', {
  method: 'POST',
  body: {
    title: 'New Post',
    content: 'Content here...'
  }
})
```

## 🎯 Key Features Implemented

### Public Frontend
- ✅ Homepage with hero banner
- ✅ Posts list with pagination
- ✅ Post detail with comments
- ✅ Categories & tags
- ✅ Archive by date
- ✅ User authentication (login/register)
- ✅ Multi-language support (i18n)
- ✅ Responsive design

### Admin Panel
- ✅ Dashboard with statistics
- ✅ Admin layout with sidebar
- 🚧 Posts management (CRUD)
- 🚧 Categories management
- 🚧 Tags management
- 🚧 Comments moderation
- 🚧 Site settings

### OOBE (Onboarding)
- ✅ Installation wizard
- ✅ Database configuration
- ✅ Admin account creation
- ✅ Real-time progress tracking

## 📝 TODO: Remaining Pages

Create these pages to complete the frontend:

```bash
# Category & Tag Details
app/pages/categories/[slug].vue
app/pages/tags/[slug].vue

# User Profile
app/pages/profile/index.vue
app/pages/profile/posts.vue
app/pages/profile/settings.vue

# Static Pages
app/pages/about.vue
app/pages/friends.vue
app/pages/guestbook.vue
app/pages/gallery.vue

# Admin CRUD Pages
app/pages/admin/posts/index.vue
app/pages/admin/posts/create.vue
app/pages/admin/posts/[id]/edit.vue
app/pages/admin/categories.vue
app/pages/admin/tags.vue
app/pages/admin/comments.vue
app/pages/admin/users.vue
app/pages/admin/settings.vue
```

## 🔍 Debugging Tips

### API Connection Issues

```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS headers
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://localhost:8000/api/posts
```

### Clear Auth State

```javascript
// In browser console
localStorage.removeItem('access_token')
localStorage.removeItem('refresh_token')
location.reload()
```

### View Nuxt DevTools

Press `Shift + Alt + D` in development mode

## 🚀 Deployment

### Static Site Generation (SSG)

```bash
pnpm generate
# Output in .output/public/
```

### Server-Side Rendering (SSR)

```bash
pnpm build
node .output/server/index.mjs
```

### Environment Variables (Production)

```env
API_BASE_URL=https://api.yourdomain.com/api
NUXT_PUBLIC_API_BASE=https://api.yourdomain.com/api
NODE_ENV=production
```

## 📚 Additional Resources

- [Nuxt 4 Documentation](https://nuxt.com/docs)
- [NuxtUI Documentation](https://ui.nuxt.com)
- [Tailwind CSS Documentation](https://tailwindcss.com)
- [Pinia Documentation](https://pinia.vuejs.org)

## 🆘 Support

For issues or questions:
1. Check the `IMPLEMENTATION.md` file
2. Review backend API at `http://localhost:8000/docs`
3. Check browser console for errors
4. Verify backend is running and accessible

---

**Status**: 🟢 Core frontend infrastructure complete and functional
**Next**: Complete remaining CRUD pages and admin panel features
