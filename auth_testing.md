# Auth testing notes
- Login: POST /api/auth/login {email,password} -> sets httpOnly cookies access_token/refresh_token (SameSite=Lax, Secure)
- If 2FA enabled: first response {requires_2fa:true}; resend with totp
- 5 failed attempts per ip+email => 15 min lockout (429)
- Credentials: /app/memory/test_credentials.md
- Mongo check: db.users.findOne({role:"super_admin"}) password_hash starts with $2b$
- Mutating /api/admin & /api/auth requests with a foreign Origin header are rejected (403)
