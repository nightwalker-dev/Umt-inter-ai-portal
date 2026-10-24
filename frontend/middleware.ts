import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith('/admin')) {
    // Check for auth token in cookies (assuming Supabase sets it or we set it)
    const supabaseAuthCookie = request.cookies.get('sb-access-token');

    // Allow access to login page
    if (pathname === '/admin/login') {
      if (supabaseAuthCookie) {
        return NextResponse.redirect(new URL('/admin', request.url));
      }
      return NextResponse.next();
    }

    // Redirect to login if not authenticated
    if (!supabaseAuthCookie) {
      return NextResponse.redirect(new URL('/admin/login', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*'],
};
