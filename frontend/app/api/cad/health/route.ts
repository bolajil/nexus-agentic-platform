import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8003';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/cad/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!res.ok) {
      return NextResponse.json(
        { freecad_available: false, zoo_api_configured: false },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('CAD health check failed:', error);
    return NextResponse.json(
      { freecad_available: false, zoo_api_configured: false },
      { status: 500 }
    );
  }
}
