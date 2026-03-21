import { NextRequest, NextResponse } from 'next/server';

// Routes that don't require authentication
const PUBLIC_PATHS = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublic = PUBLIC_PATHS.some(p => pathname.startsWith(p));
  // The presence cookie is set by AuthContext on successful login.
  // Real token verification happens on the backend for every API call.
  const isLoggedIn = request.cookies.has('nexus_logged_in');

  // Logged-in user visiting login/register → redirect to home
  if (isPublic && isLoggedIn) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Unauthenticated user visiting a protected route → redirect to login
  if (!isPublic && !isLoggedIn) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('from', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Apply to all routes except Next.js internals and static assets
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.png$).*)'],
};
