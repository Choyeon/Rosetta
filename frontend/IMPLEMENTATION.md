# Rosetta Frontend - Implementation Guide

## 🎉 Project Setup Complete!

The Nuxt 4 frontend for Rosetta blog system has been initialized with the following structure:

### ✅ Completed Components

1. **Project Configuration**
   - Nuxt 4 with NuxtUI template
   - TypeScript support
   - Pinia state management
   - i18n internationalization (zh/en/ja/zh_Hant)
   - API integration with backend

2. **Core Files Created**
   - `types/api.ts` - Complete TypeScript definitions
   - `stores/auth.ts` - Authentication store with JWT
   - `composables/useAPI.ts` - API wrapper with auth interceptor
   - `composables/usePosts.ts` - Post management functions
   - `composables/useCore.ts` - Categories, Tags, Navigation, etc.
   - `composables/useOOBE.ts` - OOBE installation functions

3. **Layouts**
   - `layouts/default.vue` - Main blog layout
   - `layouts/admin.vue` - Admin panel layout

4. **Pages Created**
   - `pages/index.vue` - Homepage with hero banner, featured posts
   - `pages/login.vue` - Login page
   - `pages/oobe.vue` - OOBE installation wizard
   - `pages/posts/[slug].vue` - Post detail page with comments

5. **Components**
   - `AppHeader.vue` - Navigation header with auth menu
   - `AppFooter.vue` - Footer with stats and links
   - `PostCard.vue` - Reusable post card component

6. **i18n Locales**
   - Complete translations for zh, en, ja, zh_Hant

### 📋 Remaining Tasks

To complete the frontend, create these additional files:

#### Essential Pages

```bash
# Posts & Categories
app/pages/posts/index.vue          # Posts list page
app/pages/categories/index.vue     # Categories page
app/pages/categories/[slug].vue    # Category detail
app/pages/tags/index.vue           # Tags page
app/pages/tags/[slug].vue          # Tag detail
app/pages/archive.vue              # Archive page

# User Pages
app/pages/register.vue             # Registration
app/pages/profile/index.vue        # User profile
app/pages/profile/posts.vue        # User's posts
app/pages/profile/settings.vue     # User settings

# Static Pages
app/pages/about.vue                # About page
app/pages/friends.vue              # Friend links
app/pages/guestbook.vue            # Guestbook
app/pages/gallery.vue              # Gallery
app/pages/dynamic.vue              # Dynamic/Activity feed

# Admin Pages (with NuxtUI)
app/pages/admin/index.vue          # Admin dashboard
app/pages/admin/posts/index.vue    # Posts management
app/pages/admin/posts/create.vue   # Create post
app/pages/admin/posts/[id]/edit.vue # Edit post
app/pages/admin/categories.vue     # Categories management
app/pages/admin/tags.vue           # Tags management
app/pages/admin/comments.vue       # Comments moderation
app/pages/admin/users.vue          # Users management
app/pages/admin/settings.vue       # Site settings
```

#### Additional Components

```bash
components/CommentItem.vue         # Single comment display
components/AdminSidebar.vue        # Admin sidebar navigation
components/AdminHeader.vue         # Admin header
components/MarkdownEditor.vue      # Markdown editor for posts
components/ImageUploader.vue       # Image upload component
```

### 🚀 Quick Start

```bash
# Install dependencies
cd frontend
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build

# Preview production build
pnpm preview
```

### 🔧 Configuration

1. **Environment Variables** (`.env`)
```env
API_BASE_URL=http://localhost:8000/api
```

2. **Backend Connection**
- Ensure backend is running on `http://localhost:8000`
- API endpoints are automatically prefixed with `/api`

3. **OOBE Setup**
- First visit: Navigate to `/oobe` for installation
- Follow the wizard to configure database and admin account

### 🎨 Design System

**Color Palette** (from design_sense):
- Background: `#F7F5F1` (soft off-white)
- Surface: `#FFFFFF` (white)
- Border: `#E7E3DA` (hairline)
- Text: `#1E2227` (ink)
- Muted: `#6B7077` (secondary text)
- Accent: `#3C5A78` (muted slate blue)
- Hover: `#2E4760` (darker slate)

**Typography**:
- Headings: Playfair Display (serif, 500-700)
- Body: Inter (400-500)

**Components** (NuxtUI v4):
- Use `UButton`, `UInput`, `UCard`, etc. for consistent styling
- Admin panel uses NuxtUI components
- Public pages use custom styled components

### 📱 Responsive Design

- Mobile-first approach
- Breakpoints: sm(640px), md(768px), lg(1024px)
- Mobile navigation with slide-over menu
- Optimized for touch targets (44px minimum)

### 🌐 API Integration

All API calls go through `useAPI` composable:
- Automatic auth token injection
- 401 error handling with token refresh
- Language header injection
- Error handling

Example:
```typescript
const { data, error, refresh } = await useAPI('/posts', {
  query: { page: 1, page_size: 12 }
})
```

### 🔐 Authentication Flow

1. User logs in → JWT tokens stored in localStorage
2. `useAuthStore` manages auth state
3. `useAPI` automatically adds `Authorization` header
4. On 401 error → attempts token refresh
5. If refresh fails → redirects to login

### 📦 Dependencies Installed

```json
{
  "@nuxtjs/i18n": "^9.2.1",
  "@vueuse/core": "^11.3.0",
  "@nuxt/ui": "^4.10.0",
  "pinia": "^2.2.8",
  "marked": "For markdown rendering",
  "zod": "For validation"
}
```

### 🎯 Next Steps

1. **Complete remaining pages** - Use existing pages as templates
2. **Add markdown editor** - For admin post creation
3. **Implement image upload** - Media management
4. **Add search functionality** - Global search
5. **Implement RSS feed** - `/rss` endpoint
6. **Add dark mode** - Toggle between themes
7. **Optimize images** - Lazy loading, responsive images
8. **Add animations** - Page transitions, micro-interactions
9. **SEO optimization** - Meta tags, structured data
10. **Testing** - Unit tests, E2E tests

### 📚 Code Examples

#### Creating a new page with API data:

```vue
<template>
  <div>
    <h1>{{ t('common.categories') }}</h1>
    <div v-if="pending">Loading...</div>
    <div v-else-if="categories">
      <CategoryCard 
        v-for="cat in categories" 
        :key="cat.id"
        :category="cat"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
const { t, locale } = useI18n()
const { getCategories } = useCategories()

const { data: categories, pending } = await getCategories()

const getLocalizedValue = (value: any) => {
  if (typeof value === 'string') return value
  return value?.[locale.value] || value?.zh || ''
}
</script>
```

#### Admin page with auth guard:

```vue
<template>
  <div>
    <h1>Admin Dashboard</h1>
    <!-- Admin content -->
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'admin',
  middleware: 'auth-admin'
})

const authStore = useAuthStore()

if (!authStore.isAdmin) {
  navigateTo('/')
}
</script>
```

### 🐛 Troubleshooting

**API Connection Issues:**
- Check backend is running: `http://localhost:8000/docs`
- Verify `.env` has correct `API_BASE_URL`
- Check browser console for CORS errors

**OOBE Not Working:**
- Ensure backend OOBE is not completed
- Check backend `.oobe_complete` file doesn't exist

**Authentication Issues:**
- Clear localStorage: `localStorage.clear()`
- Check token expiration in network tab
- Verify backend JWT settings

### 🎨 Customization

**Change theme colors:**
Edit `app.config.ts`:
```typescript
export default defineAppConfig({
  ui: {
    primary: 'blue',
    gray: 'slate'
  }
})
```

**Modify typography:**
Edit `app/assets/css/main.css`:
```css
@import 'tailwindcss';

@theme {
  --font-family-serif: 'Playfair Display', serif;
  --font-family-sans: 'Inter', sans-serif;
}
```

### 📝 Notes

- All backend API endpoints are available via composables
- TypeScript types match backend Pydantic schemas
- i18n keys match backend locale structure
- Admin panel uses NuxtUI components for consistency
- Public pages use custom styled components for uniqueness

---

**Project Status:** ✅ Core infrastructure complete, ready for feature development

**Next Milestone:** Complete all CRUD pages and admin panel functionality
