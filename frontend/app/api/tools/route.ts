import { NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8003';

export async function GET() {
  try {
    const r = await fetch(`${BACKEND}/api/v1/tools`);
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json([], { status: 200 });
  }
}
