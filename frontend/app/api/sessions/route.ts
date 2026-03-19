import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

export async function POST(req: NextRequest) {
  const body = await req.json();

  const upstream = await fetch(`${BACKEND}/api/v1/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    // @ts-expect-error — node-fetch duplex
    duplex: 'half',
  });

  const sessionId = upstream.headers.get('X-Session-ID') || '';

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
      'X-Session-ID': sessionId,
    },
  });
}

export async function GET() {
  const upstream = await fetch(`${BACKEND}/api/v1/sessions`);
  const data = await upstream.json();
  return NextResponse.json(data);
}
