import { NextRequest, NextResponse } from 'next/server';

const BACKEND = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const project_id = searchParams.get('project_id');
  const domain = searchParams.get('domain');

  const params = new URLSearchParams();
  if (project_id) params.set('project_id', project_id);
  if (domain) params.set('domain', domain);

  const upstream = await fetch(`${BACKEND}/api/v1/documents?${params}`);
  return NextResponse.json(await upstream.json());
}

export async function POST(req: NextRequest) {
  // Forward multipart FormData directly — do not re-encode as JSON
  const formData = await req.formData();

  const upstream = await fetch(`${BACKEND}/api/v1/documents/upload`, {
    method: 'POST',
    body: formData,
  });

  const data = await upstream.json();
  return NextResponse.json(data, { status: upstream.status });
}
