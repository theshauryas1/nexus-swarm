"""
agent_security_prompt.py — Security System Prompt for Agent-Generated Code
All agents that generate code (BackendAgent, FrontendAgent, APIAgent, DeployAgent)
receive this appended to their system prompt automatically.

IMPORTANT: This does NOT change agent behaviour for their primary task.
It only appends a security checklist to what they must follow when writing code.
"""

# This is appended to the system prompt of every code-generating agent
CODING_SECURITY_RULES = """
─── MANDATORY SECURITY RULES ─────────────────────────────────────────────────
You MUST follow ALL of these rules in every piece of code you generate.
Violations will be rejected by the SecurityManager pipeline.

1. SECRETS & ENVIRONMENT VARIABLES
   - NEVER hardcode API keys, tokens, passwords, or secrets in code.
   - All secrets must be accessed via environment variables: os.environ.get("KEY") or process.env.KEY
   - Generate a .env.example with empty values for all required vars.
   - .env files must always be in .gitignore.

2. RATE LIMITING
   - Apply rate limiting on ALL public API endpoints.
   - Auth routes (login, register): 5 requests per 15 minutes per IP.
   - General API: 60 requests per minute per IP.
   - AI/LLM endpoints: 10 requests per minute per user.
   - Always return 429 with Retry-After header when limit is hit.
   - Python/FastAPI: use slowapi. Node/Express: use express-rate-limit.

3. INPUT VALIDATION & SANITIZATION
   - Validate ALL inputs server-side using Pydantic (Python) or Zod (TypeScript).
   - Sanitize string inputs to prevent XSS before storing or displaying.
   - Use parameterized queries or ORM. NEVER interpolate user data into raw SQL.
   - Validate file uploads: check MIME type, extension, and size (5MB images, 25MB docs).

4. AUTHENTICATION & AUTHORIZATION
   - Use established auth libraries: NextAuth, Clerk, Supabase Auth, Passport.js, or PyJWT.
   - Passwords must use bcrypt (min cost 12) or argon2. NEVER store plain text.
   - JWTs: sign with strong secret (min 32 chars), set short expiry (15-60 min).
   - Store refresh tokens in httpOnly cookies, NEVER in localStorage.
   - Check both identity AND permission on every protected request.

5. SQL & DATABASE SECURITY
   - Use an ORM (Prisma, SQLAlchemy, Drizzle) or parameterized queries ONLY.
   - NEVER construct queries via string concatenation with user data.
   - Apply principle of least privilege for database users.
   - NEVER return raw database errors to the client.

6. CORS CONFIGURATION
   - NEVER use wildcard CORS (*) in production.
   - Explicitly whitelist only the origins that must access your API.
   - Restrict allowed HTTP methods to only what each endpoint needs.

7. HTTP SECURITY HEADERS
   - Always set: Content-Security-Policy, X-Frame-Options: DENY, X-Content-Type-Options: nosniff,
     Strict-Transport-Security, Referrer-Policy: strict-origin-when-cross-origin.
   - Remove X-Powered-By header.
   - Python/FastAPI: add SecurityHeadersMiddleware. Node: use helmet.

8. FILE UPLOAD SECURITY (if implementing uploads)
   - Validate MIME type AND extension on the server — never trust the client.
   - Enforce strict size limits (5MB for images, 25MB for documents).
   - Store files outside web root or in cloud storage (S3, GCS).
   - Rename uploaded files to a UUID. Never use the original filename.

9. ERROR HANDLING
   - Return ONLY generic messages to clients: "Something went wrong."
   - Log full error details server-side with timestamp, route, and sanitized context.
   - Use correct status codes: 400 for validation, 401/403 for auth, 500 for server.
   - NEVER return stack traces, database schemas, or internal paths to clients.

10. XSS PREVENTION (Frontend)
    - NEVER use dangerouslySetInnerHTML in React unless content is fully sanitized with DOMPurify.
    - NEVER use eval(), new Function(), or innerHTML with dynamic user content.
    - Avoid inline script tags — move JS to external files for CSP enforcement.

11. AI / LLM SPECIFIC (if your app uses LLMs)
    - Sanitize all user input before sending to LLM to prevent prompt injection.
    - Store LLM API keys server-side ONLY. Route all LLM calls through your own backend.
    - Always set max_tokens limits to prevent runaway costs.
    - Validate and sanitize LLM output before rendering it in the UI.

12. DEPLOYMENT CHECKLIST
    - .env is NOT committed to git.
    - Debug mode and development logging are OFF in production.
    - Database is NOT publicly exposed.
    - HTTPS is enforced.
    - Rate limiting is active on all public endpoints.
    - Unused API routes are removed or protected.
─────────────────────────────────────────────────────────────────────────────
"""


def get_secure_system_prompt(base_system: str) -> str:
    """
    Appends the mandatory security rules to any agent system prompt.
    Call this for all code-generating agents.
    """
    return base_system.rstrip() + "\n\n" + CODING_SECURITY_RULES
