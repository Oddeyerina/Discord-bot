'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { api } from '@/lib/api';
import { pages } from '@/lib/navigation';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState('');
  const pathname = usePathname();
  const router = useRouter();
  const title = pages.find(page => page.href === pathname)?.label || 'Dashboard';
  useEffect(() => {
    api<{ username: string }>('/auth/me').then(user => setUsername(user.username))
      .catch(() => { location.href = '/login'; });
  }, []);
  if (!username) return <p className="p-8">Loading dashboard…</p>;
  async function logOut() {
    await api('/auth/logout', { method: 'POST' });
    router.push('/login');
  }
  return <div className="min-h-screen md:flex"><Sidebar />
    <div className="min-w-0 flex-1">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4 md:px-10">
        <p className="font-semibold text-slate-100">{title}</p>
        <details className="relative"><summary className="cursor-pointer list-none rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-100 hover:bg-slate-800">{username}</summary>
          <div className="absolute right-0 z-20 mt-2 min-w-36 rounded-lg border border-slate-700 bg-slate-900 p-1 shadow-lg">
            <button type="button" className="w-full text-left text-sm hover:bg-slate-800" onClick={logOut}>Log out</button>
          </div>
        </details>
      </header>
      <main className="mx-auto w-full max-w-7xl space-y-6 p-6 md:p-10">{children}</main>
    </div>
  </div>;
}
