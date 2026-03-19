import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

export async function GET(_: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const upstream = await fetch(`${BACKEND}/api/v1/sessions/${id}`);
  if (!upstream.ok) return NextResponse.json({ detail: 'Not found' }, { status: 404 });
  return NextResponse.json(await upstream.json());
}

export async function DELETE(_: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  await fetch(`${BACKEND}/api/v1/sessions/${id}`, { method: 'DELETE' });
  return new NextResponse(null, { status: 204 });
}
