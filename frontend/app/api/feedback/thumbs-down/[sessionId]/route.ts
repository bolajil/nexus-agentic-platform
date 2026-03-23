import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

export async function POST(
  request: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  const { sessionId } = params;
  const { searchParams } = new URL(request.url);
  const userId = searchParams.get('user_id') || '';

  try {
    const res = await fetch(
      `${BACKEND_URL}/api/v1/feedback/thumbs-down/${sessionId}?user_id=${userId}`,
      { method: 'POST' }
    );
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Thumbs down feedback failed:', error);
    return NextResponse.json({ error: 'Feedback failed' }, { status: 500 });
  }
}
