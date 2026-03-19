import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

export async function DELETE(_: NextRequest, { params }: { params: { id: string } }) {
  const upstream = await fetch(`${BACKEND}/api/v1/documents/${params.id}`, { method: 'DELETE' });
  if (!upstream.ok) {
    const body = await upstream.json().catch(() => ({}));
    return NextResponse.json(body, { status: upstream.status });
  }
  return new NextResponse(null, { status: 204 });
}
