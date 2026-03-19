import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8003';

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const url = new URL(req.url);
  const action = url.searchParams.get('action') || 'connect';  // connect | test

  let body: object = {};
  try { body = await req.json(); } catch { /* empty body is fine */ }

  const r = await fetch(`${BACKEND}/api/v1/tools/${id}/${action}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await r.json().catch(() => ({ error: 'invalid response' }));
  return NextResponse.json(data, { status: r.ok ? 200 : r.status });
}

export async function DELETE(_: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const r = await fetch(`${BACKEND}/api/v1/tools/${id}/connect`, { method: 'DELETE' });
  return NextResponse.json(await r.json());
}

export async function GET(_: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const r = await fetch(`${BACKEND}/api/v1/tools/${id}/status`);
  return NextResponse.json(await r.json());
}
