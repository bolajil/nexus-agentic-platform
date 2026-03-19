import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

export async function GET(_: NextRequest, { params }: { params: { id: string } }) {
  const upstream = await fetch(`${BACKEND}/api/v1/sessions/${params.id}`);
  if (!upstream.ok) return NextResponse.json({ detail: 'Not found' }, { status: 404 });
  return NextResponse.json(await upstream.json());
}

export async function DELETE(_: NextRequest, { params }: { params: { id: string } }) {
  await fetch(`${BACKEND}/api/v1/sessions/${params.id}`, { method: 'DELETE' });
  return new NextResponse(null, { status: 204 });
}
