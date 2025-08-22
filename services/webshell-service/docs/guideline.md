/src
  /app
    /(public)         # Public routes (landing, marketing, docs)
      /about
      /contact
    /(auth)           # Authentication-related routes
      /login
      /register
    /(dashboard)      # Protected routes for logged-in users
      /projects
      /settings
    layout.tsx        # Global layout
    page.tsx          # Root entry page

  /components         # Reusable UI components
    /ui               # Generic UI (buttons, modals, forms)
    /layout           # Navigation, headers, sidebars
    /charts           # Specific reusable widgets

  /features           # Business-domain features (each self-contained)
    /auth
      components/
      hooks/
      services/
      types.ts
    /projects
      components/
      hooks/
      services/
      types.ts

  /lib                # Shared helpers and utilities
    api-client.ts
    constants.ts
    auth.ts
    logger.ts

  /services           # Integration with external systems
    /database
      prisma.ts
    /cache
      redis.ts
    /third-party
      stripe.ts
      sendgrid.ts

  /hooks              # Global reusable hooks (non-feature specific)
    useDebounce.ts
    useAuth.ts

  /types              # Shared TypeScript types/interfaces
    user.ts
    project.ts

  /config             # App-wide config
    env.ts
    next.config.js

  /tests              # Unit and integration tests
    /components
    /features

/public               # Static assets (images, icons, fonts)

/prisma               # Prisma schema & migrations (if using Prisma)

/scripts              # Deployment, DB seeds, or automation scripts
