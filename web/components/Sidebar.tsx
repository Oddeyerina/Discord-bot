'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { pages } from '@/lib/navigation';

const groups = [null, 'Community', 'Voice', 'Moderation', 'System'] as const;

export default function Sidebar() {
  const pathname = usePathname();
  return <aside className="w-full shrink-0 border-b border-slate-800 bg-slate-900 md:min-h-screen md:w-64 md:border-b-0 md:border-r">
    <div className="border-b border-slate-800 px-6 py-5 text-lg font-bold tracking-tight">Morpho-Dashboard</div>
    <nav aria-label="Dashboard navigation" className="space-y-4 p-4">
      {groups.map(group => <div className={group ? 'border-t border-slate-800 pt-4' : ''} key={group || 'overview'}>
        {group && <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-widest text-slate-400">{group}</p>}
        {pages.filter(page => page.group === group).map(page =>
          <Link key={page.href} href={page.href} aria-current={pathname === page.href ? 'page' : undefined}
            className={`block rounded-lg px-3 py-2 text-sm ${pathname === page.href ? 'bg-indigo-500 text-white' : 'text-slate-100 hover:bg-slate-800'}`}>{page.label}</Link>
        )}
      </div>)}
    </nav>
  </aside>;
}
