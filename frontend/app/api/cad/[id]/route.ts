import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8003';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const url = new URL(req.url);
  const file = url.searchParams.get('file') || 'status';

  try {
    const r = await fetch(`${BACKEND}/api/v1/cad/${id}/${file}`, {
      headers: { 'User-Agent': 'NEXUS-Frontend/1.0' },
    });

    if (!r.ok) {
      if (file === 'status') return NextResponse.json({ available: false });
      return new NextResponse(null, { status: 404 });
    }

    const contentType = r.headers.get('content-type') || 'application/octet-stream';

    if (contentType.includes('json')) {
      return NextResponse.json(await r.json());
    }

    // Binary file — stream through
    const buffer = await r.arrayBuffer();
    return new NextResponse(buffer, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition':
          r.headers.get('content-disposition') || `attachment; filename="${file}"`,
        'Cache-Control': 'no-store',
      },
    });
  } catch {
    if (file === 'status') return NextResponse.json({ available: false });
    return new NextResponse(null, { status: 502 });
  }
}
