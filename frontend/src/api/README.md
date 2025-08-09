# API Authentication Configuration

## Token Handling

This application uses a standardized token handling system across all API calls.

### Token Storage Keys
- **Access Token**: `access_token` - The main JWT token used for API authentication
- **Refresh Token**: `refresh_token` - Used to refresh expired access tokens
- **User Data**: `user` - Stores the current user information

### Axios Configuration

The main axios instance is configured in `axios.ts` with:

1. **Request Interceptor**: Automatically adds the Bearer token to all requests
2. **Response Interceptor**: 
   - Handles 401 errors by attempting to refresh the token
   - If refresh fails, clears all auth data and redirects to login
   - Shows appropriate error messages for different HTTP status codes

### Usage

Always import the configured axios instance:

```typescript
import api from '../api/axios';

// Make API calls
const response = await api.get('/endpoint');
```

### Token Refresh Flow

1. When a 401 response is received, the interceptor checks for a refresh token
2. If available, it attempts to refresh the access token
3. On successful refresh, the original request is retried with the new token
4. If refresh fails, the user is logged out and redirected to login

### Important Notes

- Never use the raw axios instance - always use the configured one from `api/axios.ts`
- The `authInterceptor.ts` file is deprecated - use `axios.ts` instead
- The `services/api.ts` file is also deprecated in favor of the centralized `api/axios.ts`