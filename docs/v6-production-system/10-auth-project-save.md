# 10 — Auth + Project Save

Supabase auth flow:

- Login
- User session
- Save poster project
- Load project
- Export image

API:

```txt
POST /api/projects/save
```

DB:

```txt
poster_projects
```

Patch next:

- /dashboard/projects
- /project/[id]
- project autosave
