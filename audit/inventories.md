# Inventories Comparison vs PRD

## 1. Frontend Routes
Found Routes: ['/admin', '/admin/events', '/admin/first-login', '/admin/tasks', '/admin/timetable', '/admin/activity', '/admin/teams', '/admin/review', '/admin/availability', '/admin/users', '/admin/login']
DEFECT: Missing PRD route /admin/tasks/[id]
DEFECT: Missing PRD route /admin/events/[id]
DEFECT: Missing PRD route /admin/profile

## 2. Backend Endpoints
Found Endpoints:
 - GET /health
 - GET /me
 - POST /users
 - PATCH /users/{user_id}
 - POST /users/{user_id}/reset-password
 - POST /auth/first-password
 - GET /teams
 - GET /users
 - POST /timetable/extract
 - GET /timetable/me
 - PUT /timetable/me
 - GET /availability
 - GET /availability/free
 - POST /events
 - GET /events
 - GET /events/{event_id}
 - PATCH /events/{event_id}
 - POST /tasks
 - GET /tasks
 - GET /tasks/{task_id}
 - PATCH /tasks/{task_id}
 - POST /tasks/{task_id}/complete
 - POST /tasks/{task_id}/review
 - GET /tasks/{task_id}/history
 - GET /activity
 - GET /dashboard
DEFECT: Missing PRD endpoint PATCH /users/{id}
DEFECT: Missing PRD endpoint POST /users/{id}/reset-password
DEFECT: Missing PRD endpoint PATCH /teams/{id}
DEFECT: Missing PRD endpoint PATCH /tasks/{id}
DEFECT: Missing PRD endpoint POST /tasks/{id}/complete
DEFECT: Missing PRD endpoint POST /tasks/{id}/review
DEFECT: Missing PRD endpoint GET /tasks/{id}/history
DEFECT: Missing PRD endpoint GET /events/{id}
DEFECT: Missing PRD endpoint PATCH /events/{id}
SCOPE-DEVIATION: Extra endpoint PATCH /users/{user_id} not in PRD
SCOPE-DEVIATION: Extra endpoint POST /users/{user_id}/reset-password not in PRD
SCOPE-DEVIATION: Extra endpoint GET /events/{event_id} not in PRD
SCOPE-DEVIATION: Extra endpoint PATCH /events/{event_id} not in PRD
SCOPE-DEVIATION: Extra endpoint GET /tasks/{task_id} not in PRD
SCOPE-DEVIATION: Extra endpoint PATCH /tasks/{task_id} not in PRD
SCOPE-DEVIATION: Extra endpoint POST /tasks/{task_id}/complete not in PRD
SCOPE-DEVIATION: Extra endpoint POST /tasks/{task_id}/review not in PRD
SCOPE-DEVIATION: Extra endpoint GET /tasks/{task_id}/history not in PRD

## 3. Database Tables
Tables check complete.
