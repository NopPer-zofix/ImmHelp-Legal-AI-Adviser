// User types. The backend is the source of truth: it returns `role` from /login and must
// re-check it on every /admin request. Users without a role (older accounts) are regular users.
export const ROLES = { ADMIN: 'admin', USER: 'user' };

export const isAdmin = (user) => user?.role === ROLES.ADMIN;
