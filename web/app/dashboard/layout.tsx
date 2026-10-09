'use client';

import { useEffect, useState } from 'react';
import Sidebar from '@/components/Sidebar';
import { api } from '@/lib/api';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  useEffect(() => { api('/auth/me').then(() => setReady(true)).catch(() => { location.href = '/login'; }); }, []);
  if (!ready) return <p className="p-8">Loading dashboard…</p>;
  return <div className="min-h-screen md:flex"><Sidebar /><main className="w-full max-w-6xl space-y-6 p-6 md:p-10">{children}</main></div>;
}
