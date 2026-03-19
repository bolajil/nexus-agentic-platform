import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8003';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const query = searchParams.get('q');
  const domain = searchParams.get('domain');

  if (query) {
    const params = new URLSearchParams({ query });
    if (domain) params.set('domain', domain);
    const upstream = await fetch(`${BACKEND}/api/v1/knowledge/search?${params}`);
    return NextResponse.json(await upstream.json());
  }

  const upstream = await fetch(`${BACKEND}/api/v1/knowledge/stats`);
  return NextResponse.json(await upstream.json());
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const upstream = await fetch(`${BACKEND}/api/v1/knowledge/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return NextResponse.json(await upstream.json(), { status: upstream.status });
}
