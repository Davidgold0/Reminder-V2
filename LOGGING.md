# Logging & Database Configuration

## Overview

The application now has comprehensive logging configured across all modules. Logs are written to stdout (console) which makes them visible in Railway's log viewer.

## Database Connection Issues (Fixed)

If you see errors like:
- `Lost connection to MySQL server during query`
- `Can't reconnect until invalid transaction is rolled back`
- `ValueError: read of closed file`

These have been fixed with:
1. **Connection pooling** with pre-ping to test connections before use
2. **Automatic session cleanup** after each request
3. **Connection recycling** every hour to prevent stale connections
4. **Proper error handling** with automatic rollback on failures

## Configuration

### Environment Variable

Set the `LOG_LEVEL` environment variable to control logging verbosity:

- **DEBUG** - Most verbose, shows all debug, info, warning, error logs
- **INFO** - Shows info, warning, error logs (default for production)
- **WARNING** - Shows only warnings and errors
- **ERROR** - Shows only errors
- **CRITICAL** - Shows only critical errors

### Railway Setup

To see DEBUG logs in Railway:

1. Go to your Railway project
2. Click on your service
3. Go to **Variables** tab
4. Add a new variable:
   - **Name**: `LOG_LEVEL`
   - **Value**: `DEBUG`
5. Redeploy your service

### Local Development

For local development, create or update your `.env` file:

```bash
LOG_LEVEL=DEBUG
```

## Log Format

All logs follow this format:
```
YYYY-MM-DD HH:MM:SS - module.name - LEVEL - message
```

Example:
```
2025-11-18 10:30:45 - services.agent_tools - INFO - create_reminder called for user_phone=+1234567890, is_recurring=True
2025-11-18 10:30:45 - services.db.events - DEBUG - Event details: description='Daily standup', event_time=2025-11-19 09:00:00
```

## What's Logged

### INFO Level
- Function entry points with key identifiers
- Successful operations (created/updated/retrieved)
- Important state changes
- Business-level events

### DEBUG Level
- Detailed parameter values
- Database query details
- Internal processing steps
- Validation checks
- Intermediate results

### WARNING Level
- Invalid parameters
- Not found scenarios
- Business rule violations

### ERROR Level
- Failed database operations
- Invalid input formats
- Failed external API calls

### EXCEPTION Level
- All caught exceptions with full stack traces

## Modules with Logging

- ✅ `services/agent_tools.py` - All agent tool functions
- ✅ `services/db/users.py` - User database operations
- ✅ `services/db/events.py` - Event database operations
- ✅ `services/db/messages.py` - Message database operations

## Viewing Logs

### Railway
1. Go to your Railway project
2. Click on your service
3. Click on the **Deployments** tab
4. Click on the latest deployment
5. View logs in real-time

### Local
Logs appear in your terminal where you run the Flask application.

## Best Practices

- Use **DEBUG** level during development and troubleshooting
- Use **INFO** level in production for normal monitoring
- Use **ERROR** or **WARNING** level when you want minimal logs
- Never log sensitive information (passwords, tokens, full credit card numbers)
- Logs already avoid logging full message content (truncated to 100 chars)
