'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { pages } from '@/lib/navigation';
import { api } from '@/lib/api';

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  return <aside className="w-full shrink-0 border-b border-slate-800 bg-slate-900 p-5 md:min-h-screen md:w-64 md:border-b-0 md:border-r">
    <h1 className="mb-8 text-xl font-bold tracking-tight">dcbot-suite</h1>
    <nav className="space-y-1">{pages.map(page =>
      <Link key={page.href} href={page.href} className={`block rounded-lg px-3 py-2 text-sm ${pathname === page.href ? 'bg-indigo-500 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>{page.label}</Link>
    )}</nav>
    <button className="secondary mt-8 w-full text-sm" onClick={async () => { await api('/auth/logout', { method: 'POST' }); router.push('/login'); }}>Log out</button>
  </aside>;
}
